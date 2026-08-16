"""Register AgentLAB's public saved attacks independently of victim name."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.attacks.attack_registry import register_attack
from agentdojo.attacks.base_attacks import BaseAttack
from agentdojo.base_tasks import BaseInjectionTask, BaseUserTask
from agentdojo.task_suite.task_suite import TaskSuite
from transformers import AutoTokenizer


PACKAGE_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_ROOT = (
    PACKAGE_ROOT
    / "runs/e79_external_benchmarks/AgentLAB/Task-Injection/agentdojo/res/long_horizon/gpt-4o-backip"
)


@register_attack
class E79AgentLABSavedTransferAttack(BaseAttack):
    """Load the hash-frozen 303-pair attacks without regeneration."""

    name = "e79_agentlab_saved_transfer"

    def __init__(self, task_suite: TaskSuite, target_pipeline: BasePipelineElement) -> None:
        super().__init__(task_suite, target_pipeline)
        self.root = Path(os.getenv("E79_AGENTLAB_SAVED_ATTACK_ROOT", str(DEFAULT_ROOT)))
        self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", local_files_only=True)

    def _render_messages(self, raw_messages: list[dict[str, Any]]) -> str:
        normalized = []
        for message in raw_messages:
            if not isinstance(message, dict) or len(message) != 1:
                raise ValueError(f"invalid saved message: {message!r}")
            role, content = next(iter(message.items()))
            if not isinstance(content, str):
                content = json.dumps(content, sort_keys=True)
            normalized.append({"role": role, "content": content.replace('"', "'")})
        return self.tokenizer.apply_chat_template(normalized, tokenize=False, add_generation_prompt=False)

    def _saved_path(self, user_task: BaseUserTask, injection_task: BaseInjectionTask) -> Path:
        return (
            self.root
            / self.task_suite.name
            / "v1.2.1"
            / f"{user_task.ID}_{injection_task.ID}"
            / "newest_injection.json"
        )

    def attack(self, user_task: BaseUserTask, injection_task: BaseInjectionTask) -> dict[str, str]:
        path = self._saved_path(user_task, injection_task)
        if not path.exists():
            raise FileNotFoundError(f"saved attack is outside frozen 303-pair manifest: {path}")
        content = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(content, list) or not content:
            raise ValueError(f"malformed saved attack: {path}")

        injections = {
            candidate: self._render_messages(content[0]["content"])
            for candidate in self.get_injection_candidates(user_task)
        }
        field_map = {
            "cloud drive": ("new_insert_file_name", "new_insert_file_content"),
            "inbox": ("new_insert_email_subject", "new_insert_email_body"),
            "calendar": ("new_calendar_event_title", "new_calendar_event_description"),
            "car": (None, "travel_injection_car_rental"),
            "hotel": (None, "travel_injection_hotel"),
            "restaurant": (None, "travel_injection_restaurant"),
            "bank_file": ("bank_file_injection_name", "bank_file_injection_content"),
            "website": ("slack_injection_website_name", "slack_injection_website_content"),
            "charlie_inbox": (None, "slack_injection_charlie_content"),
        }
        for record in content[1:]:
            environment = record.get("environment")
            if environment not in field_map:
                raise ValueError(f"unsupported saved attack environment: {environment!r}")
            title_field, content_field = field_map[environment]
            if title_field is not None:
                injections[title_field] = str(record.get("title", ""))
            injections[content_field] = self._render_messages(record["content"])
        return injections
