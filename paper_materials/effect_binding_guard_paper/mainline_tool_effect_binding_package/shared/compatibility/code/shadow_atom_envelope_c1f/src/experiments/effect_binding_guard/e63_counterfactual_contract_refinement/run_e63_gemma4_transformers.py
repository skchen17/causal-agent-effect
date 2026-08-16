from __future__ import annotations

import argparse
import json
import os
import time
import weakref
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch import nn
from safetensors import safe_open
from transformers import AutoConfig, AutoTokenizer, BitsAndBytesConfig, Gemma4ForCausalLM
from transformers.models.gemma4.modeling_gemma4 import Gemma4PreTrainedModel, Gemma4TextModel

from src.experiments.effect_binding_guard.e62_local_llm_proposer_validation.local_llm_backend import LLMResponse

from . import run_e63 as e63


DEFAULT_MODEL_PATH = (
    "/data/CSK/causal-agent-safety-research/.hf_cache/hub/"
    "models--google--gemma-4-26B-A4B-it/snapshots/462a98a12e28e2cbcfccaf78fe41e3e50235e6ae"
)


class TiedEmbeddingLMHead(nn.Module):
    def __init__(self, owner: nn.Module) -> None:
        super().__init__()
        self.__dict__["_owner_ref"] = weakref.ref(owner)

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        owner = self.__dict__["_owner_ref"]()
        weight = owner.model.embed_tokens.weight
        return F.linear(hidden_states.to(weight.device), weight)


class Gemma4ForCausalLMNoStandaloneHead(Gemma4ForCausalLM):
    _tied_weights_keys: dict[str, str] = {}
    _keys_to_ignore_on_load_missing = [r"lm_head.weight"]

    def _can_set_experts_implementation(self) -> bool:
        # The dynamically defined class is used only for local inference; avoid
        # Transformers' source-file inspection path for custom expert kernels.
        return False

    def __init__(self, config):
        Gemma4PreTrainedModel.__init__(self, config)
        self.model = Gemma4TextModel(config)
        self.vocab_size = config.vocab_size
        self.lm_head = TiedEmbeddingLMHead(self)
        self.post_init()

    def tie_weights(self, *args, **kwargs) -> None:
        self.lm_head = TiedEmbeddingLMHead(self)


class Gemma4TransformersBackend:
    backend_name = "transformers_gemma4_text_only"

    def __init__(
        self,
        *,
        model_path: str,
        model_name: str,
        max_new_tokens: int,
        max_memory_gpu0: str,
        max_memory_gpu1: str,
        max_memory_cpu: str,
        quantization: str = "bf16",
        layer_split: int = 14,
        bnb_quant_type: str = "nf4",
        bnb_compute_dtype: str = "bf16",
        bnb_double_quant: bool = True,
        last_layer_on_gpu0: bool = False,
    ) -> None:
        self.model_path = Path(model_path)
        self.model = model_name
        self.max_new_tokens = max_new_tokens
        self.max_memory_gpu0 = max_memory_gpu0
        self.max_memory_gpu1 = max_memory_gpu1
        self.max_memory_cpu = max_memory_cpu
        self.quantization = quantization
        self.layer_split = layer_split
        self.bnb_quant_type = bnb_quant_type
        self.bnb_compute_dtype = bnb_compute_dtype
        self.bnb_double_quant = bnb_double_quant
        self.last_layer_on_gpu0 = last_layer_on_gpu0
        self._loaded = False
        self._load_error = ""
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self.load_diagnostics: dict[str, Any] = {}

    def health(self) -> tuple[bool, str]:
        if not self.model_path.exists():
            return False, f"model path missing: {self.model_path}"
        if not list(self.model_path.glob("model-*.safetensors")):
            return False, f"no safetensors shards under: {self.model_path}"
        try:
            self._ensure_loaded()
        except Exception as exc:  # pragma: no cover - hardware dependent
            self._load_error = f"{type(exc).__name__}: {exc}"
            return False, self._load_error
        return True, json.dumps(self.load_diagnostics, sort_keys=True)

    def complete(self, prompt: str) -> LLMResponse:
        try:
            self._ensure_loaded()
            assert self._tokenizer is not None
            assert self._model is not None
            messages = [
                {
                    "role": "user",
                    "content": (
                        "Use no-think mode. Return only the final JSON contract. "
                        "If any thinking text is unavoidable, put the final object after <FINAL_JSON>.\n\n"
                        "Use compact JSON. Omit optional fields whose value would be null, false, an empty list, "
                        "or the parser default. The minimum valid object is tool_name plus a non-empty templates "
                        "array. Each template only needs effect_type, operation, resource_field, resource_type, "
                        "and any non-default binding fields needed for target principals, commit mode, visibility, "
                        "provenance, or control source.\n\n"
                        f"{prompt}\n\n<FINAL_JSON>"
                    ),
                }
            ]
            encoded = self._tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            )
            first_device = next(iter(self._model.hf_device_map.values()))
            device = f"cuda:{first_device}" if isinstance(first_device, int) else str(first_device)
            if device.startswith("cuda"):
                encoded = {key: value.to(device) for key, value in encoded.items()}
            input_length = encoded["input_ids"].shape[-1]
            start = time.time()
            with torch.inference_mode():
                output = self._model.generate(
                    **encoded,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                    use_cache=False,
                    eos_token_id=self._tokenizer.eos_token_id,
                )
            generated = output[0, input_length:]
            text = self._tokenizer.decode(generated, skip_special_tokens=False)
            elapsed = round(time.time() - start, 3)
            return LLMResponse("ok", f"<FINAL_JSON>{text}", self.backend_name, self.model, f"elapsed_seconds={elapsed}")
        except Exception as exc:  # pragma: no cover - hardware dependent
            return LLMResponse("error", "", self.backend_name, self.model, f"{type(exc).__name__}: {exc}")

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        language_keys = language_weight_keys(self.model_path)
        key_mapping = {key: key.replace("model.language_model.", "model.", 1) for key in language_keys}
        self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_path), trust_remote_code=True)
        config = AutoConfig.from_pretrained(str(self.model_path), trust_remote_code=True).text_config
        model_cls = Gemma4ForCausalLM
        load_kwargs: dict[str, Any] = {
            "torch_dtype": torch.bfloat16,
            "device_map": "auto",
            "max_memory": {0: self.max_memory_gpu0, 1: self.max_memory_gpu1, "cpu": self.max_memory_cpu},
        }
        if self.quantization == "4bit":
            patch_bitsandbytes_params4bit()
            model_cls = Gemma4ForCausalLMNoStandaloneHead
            load_kwargs = {
                "quantization_config": BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type=self.bnb_quant_type,
                    bnb_4bit_compute_dtype=bnb_compute_dtype(self.bnb_compute_dtype),
                    bnb_4bit_use_double_quant=self.bnb_double_quant,
                ),
                "device_map": explicit_layer_device_map(self.layer_split, last_layer_on_gpu0=self.last_layer_on_gpu0),
            }
        else:
            Gemma4ForCausalLM._keys_to_ignore_on_load_missing = [r"lm_head.weight"]
        model, info = model_cls.from_pretrained(
            str(self.model_path),
            config=config,
            key_mapping=key_mapping,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
            output_loading_info=True,
            **load_kwargs,
        )
        model.tie_weights()
        model.eval()
        eager_expert_modules = 0
        for module in model.modules():
            if hasattr(module, "config") and hasattr(module.config, "_experts_implementation"):
                module.config._experts_implementation = "eager"
                eager_expert_modules += 1
        missing = [key for key in info.get("missing_keys", []) if key != "lm_head.weight"]
        unexpected_language = [key for key in info.get("unexpected_keys", []) if key.startswith("model.language_model.")]
        if missing or unexpected_language:
            raise RuntimeError(
                "invalid Gemma4 text-only load: "
                f"missing_non_lm_head={missing[:8]} unexpected_language={unexpected_language[:8]}"
            )
        self._model = model
        self._loaded = True
        self.load_diagnostics = {
            "model_path": str(self.model_path),
            "language_weight_keys": len(language_keys),
            "missing_non_lm_head": len(missing),
            "unexpected_language_keys": len(unexpected_language),
            "quantization": self.quantization,
            "bnb_quant_type": self.bnb_quant_type if self.quantization == "4bit" else "",
            "bnb_compute_dtype": self.bnb_compute_dtype if self.quantization == "4bit" else "",
            "bnb_double_quant": self.bnb_double_quant if self.quantization == "4bit" else None,
            "layer_split": self.layer_split if self.quantization == "4bit" else None,
            "last_layer_on_gpu0": self.last_layer_on_gpu0 if self.quantization == "4bit" else None,
            "experts_implementation": "eager",
            "eager_expert_modules": eager_expert_modules,
            "device_map_sample": list(model.hf_device_map.items())[:30],
            "max_memory": {"gpu0": self.max_memory_gpu0, "gpu1": self.max_memory_gpu1, "cpu": self.max_memory_cpu},
        }


def language_weight_keys(model_path: Path) -> list[str]:
    keys: list[str] = []
    for shard in sorted(model_path.glob("model-*.safetensors")):
        with safe_open(str(shard), framework="pt", device="cpu") as handle:
            keys.extend(handle.keys())
    return sorted(key for key in keys if key.startswith("model.language_model."))


def patch_bitsandbytes_params4bit() -> None:
    import bitsandbytes as bnb

    if getattr(bnb.nn.Params4bit.__new__, "_e63_patched", False):
        return
    original_new = bnb.nn.Params4bit.__new__

    def patched_new(
        cls,
        data=None,
        requires_grad=False,
        quant_state=None,
        blocksize=None,
        compress_statistics=True,
        quant_type="fp4",
        quant_storage=torch.uint8,
        module=None,
        bnb_quantized=False,
        **kwargs,
    ):
        return original_new(
            cls,
            data=data,
            requires_grad=requires_grad,
            quant_state=quant_state,
            blocksize=blocksize,
            compress_statistics=compress_statistics,
            quant_type=quant_type,
            quant_storage=quant_storage,
            module=module,
            bnb_quantized=bnb_quantized,
        )

    patched_new._e63_patched = True
    bnb.nn.Params4bit.__new__ = staticmethod(patched_new)


def bnb_compute_dtype(name: str) -> torch.dtype:
    mapping = {"bf16": torch.bfloat16, "bfloat16": torch.bfloat16, "fp16": torch.float16, "float16": torch.float16, "fp32": torch.float32, "float32": torch.float32}
    if name not in mapping:
        raise ValueError(f"unsupported bnb compute dtype: {name}")
    return mapping[name]


def explicit_layer_device_map(layer_split: int, *, last_layer_on_gpu0: bool = False) -> dict[str, int]:
    device_map: dict[str, int] = {"model.embed_tokens": 0, "model.norm": 0 if last_layer_on_gpu0 else 1}
    for index in range(30):
        device_map[f"model.layers.{index}"] = 0 if index < layer_split else 1
    if last_layer_on_gpu0:
        device_map["model.layers.29"] = 0
    return device_map


def install_gemma4_output_paths(prefix: str) -> None:
    e63.REPORT_JSON = e63.RESULTS / f"{prefix}_report.json"
    e63.REPORT_MD = e63.RESULTS / f"{prefix}_report.md"
    e63.ROUND_METRICS_CSV = e63.RESULTS / f"{prefix}_round_metrics.csv"
    e63.CANDIDATE_CONTRACTS = e63.RESULTS / f"{prefix}_candidate_contracts.jsonl"
    e63.PROMPTS_JSONL = e63.RESULTS / f"{prefix}_prompts.jsonl"
    e63.FEEDBACK_JSONL = e63.RESULTS / f"{prefix}_feedback_payloads.jsonl"
    e63.FAILURE_EXAMPLES = e63.RESULTS / f"{prefix}_failure_examples.jsonl"
    e63.FROZEN_CONTRACTS = e63.RESULTS / f"{prefix}_frozen_contracts.jsonl"
    e63.CLAIM_BOUNDARY = e63.RESULTS / f"{prefix}_claim_boundary.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E63 with a local Gemma4 Transformers text-only backend.")
    parser.add_argument("--model-path", default=os.environ.get("E63_GEMMA4_MODEL_PATH", DEFAULT_MODEL_PATH))
    parser.add_argument("--model-name", default=os.environ.get("E63_GEMMA4_MODEL_NAME", "gemma4-26b-a4b-it-text-only"))
    parser.add_argument("--tool-limit", type=int, default=int(os.environ.get("E63_GEMMA4_TOOL_LIMIT", "1")))
    parser.add_argument("--max-rounds", type=int, default=int(os.environ.get("E63_GEMMA4_MAX_ROUNDS", "0")))
    parser.add_argument("--max-new-tokens", type=int, default=int(os.environ.get("E63_GEMMA4_MAX_NEW_TOKENS", "512")))
    parser.add_argument("--prefix", default=os.environ.get("E63_GEMMA4_OUTPUT_PREFIX", "e63_gemma4_smoke"))
    parser.add_argument("--gpu0-memory", default=os.environ.get("E63_GEMMA4_GPU0_MEMORY", "16GiB"))
    parser.add_argument("--gpu1-memory", default=os.environ.get("E63_GEMMA4_GPU1_MEMORY", "16GiB"))
    parser.add_argument("--cpu-memory", default=os.environ.get("E63_GEMMA4_CPU_MEMORY", "100GiB"))
    parser.add_argument("--quantization", choices=["bf16", "4bit"], default=os.environ.get("E63_GEMMA4_QUANTIZATION", "bf16"))
    parser.add_argument("--layer-split", type=int, default=int(os.environ.get("E63_GEMMA4_LAYER_SPLIT", "14")))
    parser.add_argument("--bnb-quant-type", choices=["nf4", "fp4"], default=os.environ.get("E63_GEMMA4_BNB_QUANT_TYPE", "nf4"))
    parser.add_argument("--bnb-compute-dtype", choices=["bf16", "fp16", "fp32"], default=os.environ.get("E63_GEMMA4_BNB_COMPUTE_DTYPE", "bf16"))
    parser.add_argument("--no-double-quant", action="store_true", default=os.environ.get("E63_GEMMA4_NO_DOUBLE_QUANT", "0") == "1")
    parser.add_argument("--last-layer-on-gpu0", action="store_true", default=os.environ.get("E63_GEMMA4_LAST_LAYER_ON_GPU0", "0") == "1")
    parser.add_argument("--compact-prompt", action="store_true", default=os.environ.get("E63_COMPACT_PROMPT", "0") == "1")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    install_gemma4_output_paths(args.prefix)
    os.environ["E63_LOCAL_LLM_MODEL_PATH"] = args.model_path
    os.environ["E63_LOCAL_LLM_MAX_TOKENS"] = str(args.max_new_tokens)
    os.environ["E63_LOCAL_LLM_RESPONSE_FORMAT"] = "json_object"
    os.environ["E63_COMPACT_PROMPT"] = "1" if args.compact_prompt else "0"
    backend = Gemma4TransformersBackend(
        model_path=args.model_path,
        model_name=args.model_name,
        max_new_tokens=args.max_new_tokens,
        max_memory_gpu0=args.gpu0_memory,
        max_memory_gpu1=args.gpu1_memory,
        max_memory_cpu=args.cpu_memory,
        quantization=args.quantization,
        layer_split=args.layer_split,
        bnb_quant_type=args.bnb_quant_type,
        bnb_compute_dtype=args.bnb_compute_dtype,
        bnb_double_quant=not args.no_double_quant,
        last_layer_on_gpu0=args.last_layer_on_gpu0,
    )
    report = e63.run_e63(backend=backend, max_rounds=args.max_rounds, tool_limit=args.tool_limit)
    report["gemma4_runner"] = {
        "tool_limit": args.tool_limit,
        "max_rounds": args.max_rounds,
        "max_new_tokens": args.max_new_tokens,
        "prefix": args.prefix,
        "quantization": args.quantization,
        "layer_split": args.layer_split,
        "bnb_quant_type": args.bnb_quant_type,
        "bnb_compute_dtype": args.bnb_compute_dtype,
        "bnb_double_quant": not args.no_double_quant,
        "last_layer_on_gpu0": args.last_layer_on_gpu0,
        "compact_prompt": args.compact_prompt,
        "load_diagnostics": backend.load_diagnostics,
    }
    e63.write_outputs(
        report,
        [dict(row) for row in read_csv_dicts(e63.ROUND_METRICS_CSV)],
        [json.loads(line) for line in e63.PROMPTS_JSONL.read_text(encoding="utf-8").splitlines() if line],
        [json.loads(line) for line in e63.FEEDBACK_JSONL.read_text(encoding="utf-8").splitlines() if line],
        [json.loads(line) for line in e63.CANDIDATE_CONTRACTS.read_text(encoding="utf-8").splitlines() if line],
        [json.loads(line) for line in e63.FAILURE_EXAMPLES.read_text(encoding="utf-8").splitlines() if line],
        [json.loads(line) for line in e63.FROZEN_CONTRACTS.read_text(encoding="utf-8").splitlines() if line],
    )
    print(json.dumps({"status": report["status"], "local_llm_status": report["local_llm_status"], "report": str(e63.REPORT_JSON)}, indent=2))


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    import csv

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    main()
