#!/usr/bin/env python3
"""Local-only web interface for completing the E84 authority review packet."""

from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
import threading
import webbrowser
from collections import Counter
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from validate_e84_authority_review import payload_hash, read_jsonl, validate, validate_binding


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET_DIR = ROOT / "evaluation/e84_authority_manifests"
DEFAULT_TEMPLATE = DEFAULT_PACKET_DIR / "review_packet.template.jsonl"
DEFAULT_REVIEWED = DEFAULT_PACKET_DIR / "review_packet.reviewed.jsonl"
DEFAULT_CATALOG = DEFAULT_PACKET_DIR / "resolver_catalog.json"
DEFAULT_STATIC = DEFAULT_PACKET_DIR / "review_web"

REVIEW_KEYS = {"decision", "rationale", "source_spans", "canonical_transform", "resolver"}
HUMAN_REVIEW_KEYS = {
    "accepted",
    "notes",
    "original_task_only_confirmed",
    "review_date",
    "reviewer_anonymous_id",
}


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def review_date_valid(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    return True


class ReviewStore:
    """Hash-bound review packet store that only accepts reviewer-editable fields."""

    def __init__(self, template: Path, reviewed: Path, catalog: Path):
        self.template_path = template
        self.reviewed_path = reviewed
        self.catalog_path = catalog
        self.catalog = json.loads(catalog.read_text(encoding="utf-8"))
        self.template_rows = read_jsonl(template)
        self.template_by_key = {(row["suite"], row["user_task_id"]): row for row in self.template_rows}
        if len(self.template_by_key) != len(self.template_rows):
            raise ValueError("template contains duplicate suite/task keys")
        self.lock = threading.RLock()
        self.rows = self._load_rows()

    def _load_rows(self) -> list[dict[str, Any]]:
        if not self.reviewed_path.exists():
            return copy.deepcopy(self.template_rows)
        reviewed = read_jsonl(self.reviewed_path)
        reviewed_by_key = {(row.get("suite"), row.get("user_task_id")): row for row in reviewed}
        if len(reviewed) != len(self.template_rows) or set(reviewed_by_key) != set(self.template_by_key):
            raise ValueError("reviewed packet keys or row count differ from the immutable template")
        ordered: list[dict[str, Any]] = []
        for template_row in self.template_rows:
            key = (template_row["suite"], template_row["user_task_id"])
            row = reviewed_by_key[key]
            expected_hash = payload_hash(template_row)
            if row.get("candidate_payload_sha256") != expected_hash or payload_hash(row) != expected_hash:
                raise ValueError(f"reviewed packet changed immutable content for {key[0]}/{key[1]}")
            ordered.append(row)
        return ordered

    def _binding_errors(self, row: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for index, binding in enumerate(row.get("candidate_bindings", [])):
            errors.extend(validate_binding(binding, f"binding[{index}]", row["suite"], self.catalog))
        return errors

    def task_state(self, row: dict[str, Any]) -> dict[str, Any]:
        human = row.get("human_review") or {}
        bindings = row.get("candidate_bindings", [])
        decisions = [(binding.get("review") or {}).get("decision") for binding in bindings]
        started = any(decision in {"APPROVE", "REJECT"} for decision in decisions) or any(
            human.get(key) not in {None, "", False} for key in HUMAN_REVIEW_KEYS
        )
        metadata_complete = bool(str(human.get("reviewer_anonymous_id", "")).strip())
        metadata_complete = metadata_complete and review_date_valid(human.get("review_date"))
        metadata_complete = metadata_complete and human.get("original_task_only_confirmed") is True
        binding_errors = self._binding_errors(row) if all(decision in {"APPROVE", "REJECT"} for decision in decisions) else []
        all_decided = all(decision in {"APPROVE", "REJECT"} for decision in decisions)
        all_approved = all(decision == "APPROVE" for decision in decisions)
        complete = metadata_complete and all_decided and not binding_errors
        accepted = complete and all_approved and human.get("accepted") is True
        rejected = complete and (not all_approved or human.get("accepted") is False)
        if accepted:
            status = "accepted"
        elif rejected:
            status = "reviewed_rejected"
        elif started:
            status = "in_progress"
        else:
            status = "unreviewed"
        return {
            "status": status,
            "binding_count": len(bindings),
            "decided_bindings": sum(decision in {"APPROVE", "REJECT"} for decision in decisions),
            "binding_errors": binding_errors,
            "metadata_complete": metadata_complete,
            "all_approved": all_approved,
        }

    def progress(self) -> dict[str, Any]:
        states = [self.task_state(row) for row in self.rows]
        status_counts = Counter(state["status"] for state in states)
        binding_count = sum(state["binding_count"] for state in states)
        decided_bindings = sum(state["decided_bindings"] for state in states)
        return {
            "task_count": len(states),
            "binding_count": binding_count,
            "decided_bindings": decided_bindings,
            "status_counts": dict(sorted(status_counts.items())),
            "reviewed_packet_exists": self.reviewed_path.exists(),
        }

    def bootstrap(self) -> dict[str, Any]:
        with self.lock:
            return {
                "rows": copy.deepcopy(self.rows),
                "task_states": [self.task_state(row) for row in self.rows],
                "resolver_catalog": self.catalog,
                "progress": self.progress(),
                "reviewed_output": str(self.reviewed_path.relative_to(ROOT)),
            }

    @staticmethod
    def _validate_review_shape(review: Any) -> dict[str, Any]:
        if not isinstance(review, dict) or set(review) - REVIEW_KEYS:
            raise ValueError("binding review contains unsupported fields")
        decision = review.get("decision")
        if decision not in {"PENDING", "APPROVE", "REJECT"}:
            raise ValueError("binding decision must be PENDING, APPROVE, or REJECT")
        if not isinstance(review.get("rationale", ""), str):
            raise ValueError("binding rationale must be a string")
        spans = review.get("source_spans", [])
        if not isinstance(spans, list) or not all(isinstance(item, str) for item in spans):
            raise ValueError("source_spans must be a string list")
        if not isinstance(review.get("canonical_transform", ""), str):
            raise ValueError("canonical_transform must be a string")
        if not isinstance(review.get("resolver", {}), dict):
            raise ValueError("resolver must be an object")
        return copy.deepcopy(review)

    @staticmethod
    def _validate_human_shape(human: Any) -> dict[str, Any]:
        if not isinstance(human, dict) or set(human) - HUMAN_REVIEW_KEYS:
            raise ValueError("human_review contains unsupported fields")
        if not isinstance(human.get("accepted"), bool):
            raise ValueError("human_review.accepted must be boolean")
        if not isinstance(human.get("original_task_only_confirmed"), bool):
            raise ValueError("original_task_only_confirmed must be boolean")
        for key in ("notes", "review_date", "reviewer_anonymous_id"):
            if not isinstance(human.get(key, ""), str):
                raise ValueError(f"human_review.{key} must be a string")
        return copy.deepcopy(human)

    def save_task(self, suite: str, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) != {"binding_reviews", "human_review"}:
            raise ValueError("request must contain only binding_reviews and human_review")
        key = (suite, task_id)
        if key not in self.template_by_key:
            raise KeyError(f"unknown task {suite}/{task_id}")
        reviews = payload["binding_reviews"]
        if not isinstance(reviews, list):
            raise ValueError("binding_reviews must be a list")
        human = self._validate_human_shape(payload["human_review"])
        with self.lock:
            index = next(
                index for index, row in enumerate(self.rows)
                if (row.get("suite"), row.get("user_task_id")) == key
            )
            row = copy.deepcopy(self.rows[index])
            bindings = row.get("candidate_bindings", [])
            if len(reviews) != len(bindings):
                raise ValueError("binding review count differs from immutable candidate bindings")
            for binding, review in zip(bindings, reviews, strict=True):
                binding["review"] = self._validate_review_shape(review)
            row["human_review"] = human
            if payload_hash(row) != payload_hash(self.template_by_key[key]):
                raise ValueError("immutable task content changed")
            self.rows[index] = row
            write_jsonl_atomic(self.reviewed_path, self.rows)
            return {
                "row": copy.deepcopy(row),
                "task_state": self.task_state(row),
                "progress": self.progress(),
            }

    def validate_all(self) -> dict[str, Any]:
        with self.lock:
            if not self.reviewed_path.exists():
                return {
                    "status": "blocked_by_missing_reviewed_packet",
                    "n_errors": 1,
                    "errors": ["No reviewed packet has been saved."],
                }
            summary, _ = validate(self.template_path, self.reviewed_path, self.catalog_path)
            return summary


class ReviewServer(ThreadingHTTPServer):
    store: ReviewStore
    static_dir: Path


class ReviewHandler(BaseHTTPRequestHandler):
    server: ReviewServer

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json({"error": message}, status)

    def _serve_static(self, name: str, content_type: str) -> None:
        path = self.server.static_dir / name
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        encoded = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._serve_static("index.html", "text/html; charset=utf-8")
        elif path == "/app.js":
            self._serve_static("app.js", "text/javascript; charset=utf-8")
        elif path == "/styles.css":
            self._serve_static("styles.css", "text/css; charset=utf-8")
        elif path == "/api/bootstrap":
            self._json(self.server.store.bootstrap())
        elif path == "/api/reviewed.jsonl":
            reviewed = self.server.store.reviewed_path
            if not reviewed.exists():
                self._error(HTTPStatus.NOT_FOUND, "No reviewed packet has been saved.")
                return
            encoded = reviewed.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="review_packet.reviewed.jsonl"')
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _read_payload(self) -> dict[str, Any]:
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Content-Type must be application/json")
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2_000_000:
            raise ValueError("invalid request body length")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_payload()
            path = urlparse(self.path).path
            if path == "/api/save-task":
                if set(payload) != {"suite", "task_id", "binding_reviews", "human_review"}:
                    raise ValueError("save request contains unsupported fields")
                result = self.server.store.save_task(
                    str(payload.pop("suite")), str(payload.pop("task_id")), payload
                )
                self._json(result)
            elif path == "/api/validate":
                if payload:
                    raise ValueError("validation request must be empty")
                self._json(self.server.store.validate_all())
            else:
                self._error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
        except KeyError as exc:
            self._error(HTTPStatus.NOT_FOUND, str(exc))
        except (ValueError, json.JSONDecodeError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:  # pragma: no cover - defensive server boundary
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Server error: {exc}")


def make_server(
    host: str,
    port: int,
    template: Path = DEFAULT_TEMPLATE,
    reviewed: Path = DEFAULT_REVIEWED,
    catalog: Path = DEFAULT_CATALOG,
    static_dir: Path = DEFAULT_STATIC,
) -> ReviewServer:
    server = ReviewServer((host, port), ReviewHandler)
    server.store = ReviewStore(template, reviewed, catalog)
    server.static_dir = static_dir
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Defaults to localhost only")
    parser.add_argument("--port", type=int, default=8784)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--reviewed", type=Path, default=DEFAULT_REVIEWED)
    parser.add_argument("--resolver-catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--static-dir", type=Path, default=DEFAULT_STATIC)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = make_server(
        args.host,
        args.port,
        args.template.resolve(),
        args.reviewed.resolve(),
        args.resolver_catalog.resolve(),
        args.static_dir.resolve(),
    )
    host, port = server.server_address
    url = f"http://{host}:{port}/"
    print(f"E84 review interface: {url}")
    print(f"Reviewed output: {server.store.reviewed_path}")
    print("Press Ctrl-C to stop.")
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
