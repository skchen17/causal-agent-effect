"""T44: Stronger baselines for Auth-SafeInv held-out evaluation.

The target label for most baselines is the realized effect Omega(a, S), matching
`experiment_auth_safeinv.py`: authorization enters at evaluation time through
unauthorized positives. The direct-unauthorized baseline is reported separately
as an upper-bound style safety-supervision control.

Outputs:
  analysis/auth_baselines_<data_name>.json
  analysis/auth_baselines_<data_name>.md
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss


SKLEARN_METHODS = {
    "pooled_logistic",
    "tool_conditioned_logistic",
    "inverse_group_reweight",
    "iterative_worst_group_reweight",
    "calibrated_abstention",
    "open_set_abstain",
    "direct_unauthorized_logistic",
}
TORCH_METHODS = {"irm_linear", "domain_adversarial", "supervised_contrastive"}
ALL_METHODS = sorted(SKLEARN_METHODS | TORCH_METHODS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auth-SafeInv strong baseline comparison.")
    parser.add_argument("data_name", nargs="?", default="qwen3-8b_authorization_counterfactuals_v1")
    parser.add_argument("--evaluations", nargs="*", default=["random", "loto", "family"])
    parser.add_argument("--random-seeds", nargs="*", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--methods", nargs="*", default=ALL_METHODS)
    parser.add_argument("--min-unauth-test", type=int, default=3)
    parser.add_argument("--calibration-fpr", type=float, default=0.10)
    parser.add_argument("--torch-epochs", type=int, default=40)
    parser.add_argument("--torch-hidden-dim", type=int, default=64)
    parser.add_argument("--torch-lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def load(base: Path, data_name: str) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], list[str]]:
    x = np.load(base / "embeddings" / f"embeddings_{data_name}.npy").astype(np.float32)
    y = np.load(base / "embeddings" / f"effects_{data_name}.npy").astype(int)
    meta = json.loads((base / "embeddings" / f"meta_{data_name}.json").read_text(encoding="utf-8"))
    data_file = data_name.replace("qwen3-8b_", "")
    items = [json.loads(line) for line in (base / "data" / f"{data_file}.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(items) != len(x) or len(items) != len(y):
        raise ValueError(f"Length mismatch: items={len(items)} X={len(x)} Y={len(y)}")
    return x, y, items, list(meta["effect_names"])


def wilson_interval(k: int, n: int, z: float = 1.96) -> list[float | None]:
    if n <= 0:
        return [None, None]
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def group_random_split(items: list[dict[str, Any]], seed: int, train_frac: float = 0.8) -> tuple[np.ndarray, np.ndarray]:
    groups = np.array(sorted({item["split_group"] for item in items}))
    rng = np.random.default_rng(seed)
    rng.shuffle(groups)
    train_groups = set(groups[: int(len(groups) * train_frac)])
    train = [i for i, item in enumerate(items) if item["split_group"] in train_groups]
    test = [i for i, item in enumerate(items) if item["split_group"] not in train_groups]
    return np.array(train, dtype=int), np.array(test, dtype=int)


def validation_split(train_idx: np.ndarray, items: list[dict[str, Any]], seed: int) -> tuple[np.ndarray, np.ndarray]:
    groups = np.array(sorted({items[int(i)]["split_group"] for i in train_idx}))
    if len(groups) < 5:
        cut = max(1, int(len(train_idx) * 0.8))
        return train_idx[:cut], train_idx[cut:]
    rng = np.random.default_rng(seed)
    rng.shuffle(groups)
    val_groups = set(groups[: max(1, int(len(groups) * 0.2))])
    core = np.array([i for i in train_idx if items[int(i)]["split_group"] not in val_groups], dtype=int)
    val = np.array([i for i in train_idx if items[int(i)]["split_group"] in val_groups], dtype=int)
    if len(core) == 0 or len(val) == 0:
        cut = max(1, int(len(train_idx) * 0.8))
        return train_idx[:cut], train_idx[cut:]
    return core, val


def build_split_specs(
    items: list[dict[str, Any]],
    evaluations: list[str],
    random_seeds: list[int],
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    all_idx = np.arange(len(items), dtype=int)
    if "random" in evaluations:
        for seed in random_seeds:
            train, test = group_random_split(items, seed)
            specs.append({"split_type": "random_group", "seed": seed, "train_idx": train, "test_idx": test})
    if "loto" in evaluations:
        for tool in sorted({item["tool_name"] for item in items}):
            train = np.array([i for i, item in enumerate(items) if item["tool_name"] != tool], dtype=int)
            test = np.array([i for i, item in enumerate(items) if item["tool_name"] == tool], dtype=int)
            specs.append({"split_type": "leave_one_tool_out", "heldout_tool": tool, "train_idx": train, "test_idx": test})
    if "family" in evaluations:
        for family in sorted({item["counterfactual_family"] for item in items}):
            train = np.array([i for i, item in enumerate(items) if item["counterfactual_family"] != family], dtype=int)
            test = np.array([i for i, item in enumerate(items) if item["counterfactual_family"] == family], dtype=int)
            specs.append({"split_type": "leave_one_family_out", "heldout_family": family, "train_idx": train, "test_idx": test})
    return [spec for spec in specs if len(spec["train_idx"]) > 0 and len(spec["test_idx"]) > 0 and len(spec["train_idx"]) < len(all_idx)]


def unauthorized_labels(items: list[dict[str, Any]], effect_name: str) -> np.ndarray:
    return np.array([effect_name in item.get("unauthorized_effects", []) for item in items], dtype=int)


def absent_not_authorized_labels(items: list[dict[str, Any]], effect_name: str) -> np.ndarray:
    return np.array(
        [
            effect_name not in item.get("authorized_effects", [])
            and effect_name not in item.get("verified_effects", [])
            for item in items
        ],
        dtype=bool,
    )


def tool_onehot(items: list[dict[str, Any]], idx: np.ndarray, vocab: list[str]) -> np.ndarray:
    col = {tool: j for j, tool in enumerate(vocab)}
    out = np.zeros((len(idx), len(vocab)), dtype=np.float32)
    for row, item_idx in enumerate(idx):
        tool = items[int(item_idx)]["tool_name"]
        if tool in col:
            out[row, col[tool]] = 1.0
    return out


def fit_logistic(x_train: np.ndarray, y_train: np.ndarray, sample_weight: np.ndarray | None = None) -> LogisticRegression | None:
    if len(np.unique(y_train)) < 2:
        return None
    clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
    clf.fit(x_train, y_train, sample_weight=sample_weight)
    return clf


def inverse_group_weights(items: list[dict[str, Any]], train_idx: np.ndarray, y_train: np.ndarray) -> np.ndarray:
    keys = [(items[int(i)]["tool_name"], int(y)) for i, y in zip(train_idx, y_train)]
    counts = Counter(keys)
    weights = np.array([1.0 / counts[key] for key in keys], dtype=np.float64)
    return weights / weights.mean()


def iterative_worst_group_fit(
    x_train: np.ndarray,
    y_train: np.ndarray,
    items: list[dict[str, Any]],
    train_idx: np.ndarray,
    rounds: int = 4,
    eta: float = 1.5,
) -> LogisticRegression | None:
    if len(np.unique(y_train)) < 2:
        return None
    keys = np.array([f"{items[int(i)]['tool_name']}::{int(y)}" for i, y in zip(train_idx, y_train)])
    weights = np.ones(len(train_idx), dtype=np.float64)
    clf: LogisticRegression | None = None
    for _ in range(rounds):
        clf = fit_logistic(x_train, y_train, weights)
        if clf is None:
            return None
        proba = np.clip(clf.predict_proba(x_train)[:, 1], 1e-6, 1.0 - 1e-6)
        losses = -(y_train * np.log(proba) + (1 - y_train) * np.log(1 - proba))
        group_loss = {key: float(losses[keys == key].mean()) for key in sorted(set(keys))}
        max_loss = max(group_loss.values())
        group_weight = {key: math.exp(eta * (loss - max_loss)) for key, loss in group_loss.items()}
        weights = np.array([group_weight[key] for key in keys], dtype=np.float64)
        weights = weights / weights.mean()
    return clf


def choose_calibrated_threshold(
    proba_val: np.ndarray,
    y_effect_val: np.ndarray,
    unauth_val: np.ndarray,
    absent_val: np.ndarray,
    target_fpr: float,
) -> float:
    if int(unauth_val.sum()) == 0 or int(absent_val.sum()) == 0:
        return 0.5
    best = (1.0, 0.5, 1.0)
    for threshold in np.linspace(0.02, 0.98, 49):
        pred = proba_val >= threshold
        fnr = float(((pred == 0) & (unauth_val == 1)).sum() / max(1, int(unauth_val.sum())))
        fpr = float(((pred == 1) & absent_val).sum() / max(1, int(absent_val.sum())))
        if fpr <= target_fpr and (fnr, threshold) < (best[0], best[1]):
            best = (fnr, float(threshold), fpr)
    if best[0] < 1.0:
        return best[1]

    # If the target FPR is impossible, report the threshold with the lowest FNR,
    # tie-breaking by lower FPR.
    fallback = (1.0, 1.0, 0.5)
    for threshold in np.linspace(0.02, 0.98, 49):
        pred = proba_val >= threshold
        fnr = float(((pred == 0) & (unauth_val == 1)).sum() / max(1, int(unauth_val.sum())))
        fpr = float(((pred == 1) & absent_val).sum() / max(1, int(absent_val.sum())))
        if (fnr, fpr) < (fallback[0], fallback[1]):
            fallback = (fnr, fpr, float(threshold))
    return fallback[2]


def open_set_predict(
    *,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    items: list[dict[str, Any]],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    clf: LogisticRegression,
    percentile: float = 95.0,
) -> tuple[np.ndarray, float]:
    vocab = sorted({items[int(i)]["tool_name"] for i in train_idx})
    centroids: dict[str, np.ndarray] = {}
    train_distances = []
    for tool in vocab:
        local = np.array([pos for pos, idx in enumerate(train_idx) if items[int(idx)]["tool_name"] == tool], dtype=int)
        if len(local) == 0:
            continue
        centroid = x_train[local].mean(axis=0)
        centroids[tool] = centroid
        train_distances.extend(np.linalg.norm(x_train[local] - centroid, axis=1).tolist())
    cutoff = float(np.percentile(train_distances, percentile)) if train_distances else float("inf")
    proba = clf.predict_proba(x_test)[:, 1]
    pred = proba >= 0.5
    for pos, idx in enumerate(test_idx):
        tool = items[int(idx)]["tool_name"]
        if tool not in centroids:
            pred[pos] = True
            continue
        dist = float(np.linalg.norm(x_test[pos] - centroids[tool]))
        if dist > cutoff:
            pred[pos] = True
    return pred.astype(int), cutoff


def standardize(x_train: np.ndarray, x_test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = x_train.mean(axis=0, keepdims=True)
    std = x_train.std(axis=0, keepdims=True) + 1e-6
    return ((x_train - mean) / std).astype(np.float32), ((x_test - mean) / std).astype(np.float32)


def torch_binary_setup(y: np.ndarray) -> torch.Tensor:
    pos = max(1, int(y.sum()))
    neg = max(1, int(len(y) - y.sum()))
    return torch.tensor([neg / pos], dtype=torch.float32)


class GradReverse(torch.autograd.Function):
    @staticmethod
    def forward(ctx: Any, x: torch.Tensor, lambd: float) -> torch.Tensor:
        ctx.lambd = lambd
        return x.view_as(x)

    @staticmethod
    def backward(ctx: Any, grad_output: torch.Tensor) -> tuple[torch.Tensor, None]:
        return -ctx.lambd * grad_output, None


def grl(x: torch.Tensor, lambd: float) -> torch.Tensor:
    return GradReverse.apply(x, lambd)


def train_irm_linear(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    domain: np.ndarray,
    epochs: int,
    lr: float,
    seed: int,
) -> np.ndarray | None:
    if len(np.unique(y_train)) < 2:
        return None
    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    xt, xv = standardize(x_train, x_test)
    x_t = torch.tensor(xt, device=device)
    y_t = torch.tensor(y_train.astype(np.float32), device=device).view(-1, 1)
    x_v = torch.tensor(xv, device=device)
    model = nn.Linear(x_t.shape[1], 1).to(device)
    pos_weight = torch_binary_setup(y_train).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    domain_t = torch.tensor(domain, device=device)
    unique_domains = torch.unique(domain_t)
    for _ in range(epochs):
        logits = model(x_t)
        erm = F.binary_cross_entropy_with_logits(logits, y_t, pos_weight=pos_weight)
        penalty = torch.tensor(0.0, device=device)
        for d in unique_domains:
            mask = domain_t == d
            if int(mask.sum()) < 4 or len(torch.unique(y_t[mask])) < 2:
                continue
            scale = torch.tensor(1.0, device=device, requires_grad=True)
            loss_d = F.binary_cross_entropy_with_logits(logits[mask] * scale, y_t[mask], pos_weight=pos_weight)
            grad = torch.autograd.grad(loss_d, [scale], create_graph=True)[0]
            penalty = penalty + grad.pow(2)
        loss = erm + 0.1 * penalty
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        return torch.sigmoid(model(x_v)).detach().cpu().numpy().reshape(-1)


class DANN(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int, n_domains: int) -> None:
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(in_dim, hidden_dim), nn.ReLU())
        self.classifier = nn.Linear(hidden_dim, 1)
        self.domain = nn.Linear(hidden_dim, n_domains)

    def forward(self, x: torch.Tensor, lambd: float) -> tuple[torch.Tensor, torch.Tensor]:
        z = self.encoder(x)
        return self.classifier(z), self.domain(grl(z, lambd))


def train_domain_adversarial(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    domain: np.ndarray,
    epochs: int,
    hidden_dim: int,
    lr: float,
    seed: int,
) -> np.ndarray | None:
    if len(np.unique(y_train)) < 2 or len(np.unique(domain)) < 2:
        return None
    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    xt, xv = standardize(x_train, x_test)
    x_t = torch.tensor(xt, device=device)
    y_t = torch.tensor(y_train.astype(np.float32), device=device).view(-1, 1)
    domain_ids = {d: i for i, d in enumerate(sorted(set(domain.tolist())))}
    d_t = torch.tensor([domain_ids[int(d)] for d in domain], dtype=torch.long, device=device)
    x_v = torch.tensor(xv, device=device)
    model = DANN(x_t.shape[1], hidden_dim, len(domain_ids)).to(device)
    pos_weight = torch_binary_setup(y_train).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    for epoch in range(epochs):
        lambd = min(1.0, epoch / max(1, epochs - 1))
        logits, dom_logits = model(x_t, lambd)
        loss_y = F.binary_cross_entropy_with_logits(logits, y_t, pos_weight=pos_weight)
        loss_d = F.cross_entropy(dom_logits, d_t)
        loss = loss_y + 0.2 * loss_d
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        z = model.encoder(x_v)
        return torch.sigmoid(model.classifier(z)).detach().cpu().numpy().reshape(-1)


class SupConModel(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(in_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, hidden_dim))
        self.classifier = nn.Linear(hidden_dim, 1)


def supervised_contrastive_loss(z: torch.Tensor, labels: torch.Tensor, temperature: float = 0.2) -> torch.Tensor:
    z = F.normalize(z, dim=1)
    logits = (z @ z.T) / temperature
    logits = logits - logits.max(dim=1, keepdim=True).values.detach()
    eye = torch.eye(len(labels), device=z.device, dtype=torch.bool)
    same = labels.view(-1, 1).eq(labels.view(1, -1)) & ~eye
    exp_logits = torch.exp(logits) * (~eye)
    log_prob = logits - torch.log(exp_logits.sum(dim=1, keepdim=True) + 1e-8)
    denom = same.sum(dim=1).clamp_min(1)
    loss = -(same * log_prob).sum(dim=1) / denom
    valid = same.sum(dim=1) > 0
    if int(valid.sum()) == 0:
        return torch.tensor(0.0, device=z.device)
    return loss[valid].mean()


def train_supervised_contrastive(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    epochs: int,
    hidden_dim: int,
    lr: float,
    seed: int,
) -> np.ndarray | None:
    if len(np.unique(y_train)) < 2:
        return None
    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    xt, xv = standardize(x_train, x_test)
    x_t = torch.tensor(xt, device=device)
    y_t = torch.tensor(y_train.astype(np.float32), device=device).view(-1, 1)
    labels = torch.tensor(y_train.astype(int), device=device)
    x_v = torch.tensor(xv, device=device)
    model = SupConModel(x_t.shape[1], hidden_dim).to(device)
    pos_weight = torch_binary_setup(y_train).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    for _ in range(epochs):
        z = model.encoder(x_t)
        logits = model.classifier(z)
        loss_bce = F.binary_cross_entropy_with_logits(logits, y_t, pos_weight=pos_weight)
        loss_con = supervised_contrastive_loss(z, labels)
        loss = loss_bce + 0.05 * loss_con
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        return torch.sigmoid(model.classifier(model.encoder(x_v))).detach().cpu().numpy().reshape(-1)


def evaluate_predictions(
    *,
    items: list[dict[str, Any]],
    test_idx: np.ndarray,
    effect_name: str,
    scores: np.ndarray | None = None,
    pred: np.ndarray | None = None,
    threshold: float = 0.5,
) -> dict[str, Any] | None:
    unauth = unauthorized_labels(items, effect_name)[test_idx]
    absent = absent_not_authorized_labels(items, effect_name)[test_idx]
    n_pos = int(unauth.sum())
    if n_pos == 0:
        return None
    if pred is None:
        if scores is None:
            raise ValueError("Either scores or pred is required.")
        pred = (scores >= threshold).astype(int)
    false_neg = int(((pred == 0) & (unauth == 1)).sum())
    absent_fp = int(((pred == 1) & absent).sum())
    absent_n = int(absent.sum())
    return {
        "n_unauth_test": n_pos,
        "false_negatives": false_neg,
        "unauthorized_fnr": round(false_neg / n_pos, 4),
        "unauthorized_fnr_wilson95": wilson_interval(false_neg, n_pos),
        "not_authorized_absent_n": absent_n,
        "not_authorized_absent_fpr": None if absent_n == 0 else round(absent_fp / absent_n, 4),
        "threshold": round(float(threshold), 4),
    }


def run_split_effect(
    *,
    x: np.ndarray,
    y_all: np.ndarray,
    items: list[dict[str, Any]],
    effect_names: list[str],
    effect_idx: int,
    spec: dict[str, Any],
    methods: list[str],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    effect = effect_names[effect_idx]
    train_idx = spec["train_idx"]
    test_idx = spec["test_idx"]
    unauth_test = unauthorized_labels(items, effect)[test_idx]
    if int(unauth_test.sum()) < args.min_unauth_test:
        return []

    y_effect = y_all[:, effect_idx]
    x_train = x[train_idx]
    x_test = x[test_idx]
    y_train = y_effect[train_idx]
    domain_vocab = {tool: i for i, tool in enumerate(sorted({item["tool_name"] for item in items}))}
    domain_train = np.array([domain_vocab[items[int(i)]["tool_name"]] for i in train_idx], dtype=int)

    rows: list[dict[str, Any]] = []
    core_idx, val_idx = validation_split(train_idx, items, args.seed)

    def add_row(method: str, metric: dict[str, Any] | None, extra: dict[str, Any] | None = None) -> None:
        if metric is None:
            return
        row = {
            "split_type": spec["split_type"],
            "effect": effect,
            "method": method,
            "n_train": int(len(train_idx)),
            "n_test": int(len(test_idx)),
            **{k: v for k, v in spec.items() if k not in {"train_idx", "test_idx"}},
            **metric,
        }
        if extra:
            row.update(extra)
        rows.append(row)

    if "pooled_logistic" in methods or "calibrated_abstention" in methods or "open_set_abstain" in methods:
        clf = fit_logistic(x_train, y_train)
        if clf is not None:
            scores = clf.predict_proba(x_test)[:, 1]
            if "pooled_logistic" in methods:
                add_row("pooled_logistic", evaluate_predictions(items=items, test_idx=test_idx, effect_name=effect, scores=scores))
            if "calibrated_abstention" in methods:
                clf_cal = fit_logistic(x[core_idx], y_effect[core_idx])
                if clf_cal is not None and len(val_idx) > 0:
                    proba_val = clf_cal.predict_proba(x[val_idx])[:, 1]
                    threshold = choose_calibrated_threshold(
                        proba_val,
                        y_effect[val_idx],
                        unauthorized_labels(items, effect)[val_idx],
                        absent_not_authorized_labels(items, effect)[val_idx],
                        args.calibration_fpr,
                    )
                    scores_cal = clf_cal.predict_proba(x_test)[:, 1]
                    add_row(
                        "calibrated_abstention",
                        evaluate_predictions(
                            items=items,
                            test_idx=test_idx,
                            effect_name=effect,
                            scores=scores_cal,
                            threshold=threshold,
                        ),
                        {"target_validation_fpr": args.calibration_fpr},
                    )
            if "open_set_abstain" in methods:
                pred, cutoff = open_set_predict(
                    x_train=x_train,
                    y_train=y_train,
                    x_test=x_test,
                    items=items,
                    train_idx=train_idx,
                    test_idx=test_idx,
                    clf=clf,
                )
                add_row(
                    "open_set_abstain",
                    evaluate_predictions(items=items, test_idx=test_idx, effect_name=effect, pred=pred),
                    {"distance_cutoff_percentile": 95.0, "distance_cutoff": round(cutoff, 4)},
                )

    if "tool_conditioned_logistic" in methods:
        vocab = sorted({items[int(i)]["tool_name"] for i in train_idx})
        xt = np.hstack([x_train, tool_onehot(items, train_idx, vocab)])
        xv = np.hstack([x_test, tool_onehot(items, test_idx, vocab)])
        clf = fit_logistic(xt, y_train)
        if clf is not None:
            add_row(
                "tool_conditioned_logistic",
                evaluate_predictions(items=items, test_idx=test_idx, effect_name=effect, scores=clf.predict_proba(xv)[:, 1]),
                {"tool_vocab_size": len(vocab)},
            )

    if "inverse_group_reweight" in methods:
        weights = inverse_group_weights(items, train_idx, y_train)
        clf = fit_logistic(x_train, y_train, weights)
        if clf is not None:
            add_row(
                "inverse_group_reweight",
                evaluate_predictions(items=items, test_idx=test_idx, effect_name=effect, scores=clf.predict_proba(x_test)[:, 1]),
            )

    if "iterative_worst_group_reweight" in methods:
        clf = iterative_worst_group_fit(x_train, y_train, items, train_idx)
        if clf is not None:
            add_row(
                "iterative_worst_group_reweight",
                evaluate_predictions(items=items, test_idx=test_idx, effect_name=effect, scores=clf.predict_proba(x_test)[:, 1]),
                {"rounds": 4},
            )

    if "direct_unauthorized_logistic" in methods:
        y_unauth = unauthorized_labels(items, effect)
        clf = fit_logistic(x_train, y_unauth[train_idx])
        if clf is not None:
            add_row(
                "direct_unauthorized_logistic",
                evaluate_predictions(items=items, test_idx=test_idx, effect_name=effect, scores=clf.predict_proba(x_test)[:, 1]),
                {"training_target": "unauthorized_effect_label"},
            )

    if "irm_linear" in methods:
        scores = train_irm_linear(
            x_train,
            y_train,
            x_test,
            domain_train,
            epochs=args.torch_epochs,
            lr=args.torch_lr,
            seed=args.seed + effect_idx,
        )
        add_row("irm_linear", evaluate_predictions(items=items, test_idx=test_idx, effect_name=effect, scores=scores) if scores is not None else None)

    if "domain_adversarial" in methods:
        scores = train_domain_adversarial(
            x_train,
            y_train,
            x_test,
            domain_train,
            epochs=args.torch_epochs,
            hidden_dim=args.torch_hidden_dim,
            lr=args.torch_lr,
            seed=args.seed + effect_idx,
        )
        add_row(
            "domain_adversarial",
            evaluate_predictions(items=items, test_idx=test_idx, effect_name=effect, scores=scores) if scores is not None else None,
        )

    if "supervised_contrastive" in methods:
        scores = train_supervised_contrastive(
            x_train,
            y_train,
            x_test,
            epochs=args.torch_epochs,
            hidden_dim=args.torch_hidden_dim,
            lr=args.torch_lr,
            seed=args.seed + effect_idx,
        )
        add_row(
            "supervised_contrastive",
            evaluate_predictions(items=items, test_idx=test_idx, effect_name=effect, scores=scores) if scores is not None else None,
        )

    return rows


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["split_type"], row["method"])].append(row)
    out: list[dict[str, Any]] = []
    for (split_type, method), vals in sorted(groups.items()):
        fnr = np.array([v["unauthorized_fnr"] for v in vals], dtype=float)
        fpr_vals = [v["not_authorized_absent_fpr"] for v in vals if v["not_authorized_absent_fpr"] is not None]
        out.append(
            {
                "split_type": split_type,
                "method": method,
                "rows": len(vals),
                "mean_unauthorized_fnr": round(float(fnr.mean()), 4),
                "median_unauthorized_fnr": round(float(np.median(fnr)), 4),
                "max_unauthorized_fnr": round(float(fnr.max()), 4),
                "mean_absent_not_authorized_fpr": None if not fpr_vals else round(float(np.mean(fpr_vals)), 4),
                "mean_n_unauth_test": round(float(np.mean([v["n_unauth_test"] for v in vals])), 2),
            }
        )
    return out


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Auth-SafeInv Strong Baselines",
        "",
        f"- Data: `{payload['data_name']}`",
        f"- Samples: {payload['n_samples']}",
        f"- Methods: {', '.join(payload['methods'])}",
        f"- Torch epochs: {payload['torch_epochs']}",
        "",
        "## Aggregate",
        "",
        "| Split | Method | Rows | Mean FNR | Median FNR | Max FNR | Mean absent FPR | Mean N unauth |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["aggregate"]:
        lines.append(
            f"| `{row['split_type']}` | `{row['method']}` | {row['rows']} | "
            f"{row['mean_unauthorized_fnr']} | {row['median_unauthorized_fnr']} | {row['max_unauthorized_fnr']} | "
            f"{row['mean_absent_not_authorized_fpr']} | {row['mean_n_unauth_test']} |"
        )

    lines.extend(["", "## Caveats", ""])
    for caveat in payload["caveats"]:
        lines.append(f"- {caveat}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    base = Path(__file__).resolve().parent.parent
    methods = [m for m in args.methods if m in ALL_METHODS]
    unknown = sorted(set(args.methods) - set(methods))
    if unknown:
        raise ValueError(f"Unknown methods: {unknown}")
    torch.set_num_threads(4)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    x, y_all, items, effect_names = load(base, args.data_name)
    specs = build_split_specs(items, args.evaluations, args.random_seeds)
    rows: list[dict[str, Any]] = []
    for spec_id, spec in enumerate(specs, start=1):
        print(f"[{spec_id}/{len(specs)}] {spec['split_type']} { {k:v for k,v in spec.items() if k not in {'train_idx','test_idx'}} }", flush=True)
        for effect_idx, effect in enumerate(effect_names):
            new_rows = run_split_effect(
                x=x,
                y_all=y_all,
                items=items,
                effect_names=effect_names,
                effect_idx=effect_idx,
                spec=spec,
                methods=methods,
                args=args,
            )
            if new_rows:
                print(f"  {effect}: {len(new_rows)} method rows", flush=True)
            rows.extend(new_rows)

    payload = {
        "data_name": args.data_name,
        "n_samples": len(items),
        "effect_names": effect_names,
        "evaluations": args.evaluations,
        "methods": methods,
        "torch_epochs": args.torch_epochs,
        "rows": rows,
        "aggregate": aggregate(rows),
        "caveats": [
            "Most baselines train on realized effect labels and are evaluated on unauthorized-effect positives, matching Auth-SafeInv's effect-probe framing.",
            "`direct_unauthorized_logistic` trains directly on unauthorized labels and should be treated as an upper-bound safety-supervision control, not the same setting as effect detection.",
            "`iterative_worst_group_reweight` is a linear worst-group reweighting baseline, not a formal GroupDRO certificate.",
            "`open_set_abstain` can degenerate into rejecting all held-out-tool examples; interpret FNR=0/FPR=1 as an unusable safety/utility tradeoff, not a mitigation win.",
            "Torch baselines use compact full-batch pilots; for final paper claims, rerun with seed variance and hyperparameter sweeps.",
            "All metrics are fixed-threshold diagnostics except `calibrated_abstention`, which tunes a threshold on held-out training groups.",
        ],
    }
    out_json = base / "analysis" / f"auth_baselines_{args.data_name}.json"
    out_md = base / "analysis" / f"auth_baselines_{args.data_name}.md"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Saved JSON: {out_json}")
    print(f"Saved MD:   {out_md}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
