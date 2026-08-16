#!/usr/bin/env python3
"""Local-only web UI for independent E85 security-effect projection review."""

from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
import threading
import webbrowser
from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from validate_e85_projection_review import payload_hash, read_jsonl, validate, validate_review, write_outputs


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "evaluation/e85_security_effect_projections"
DEFAULT_TEMPLATE = DEFAULT_DIR / "review_packet.template.jsonl"
DEFAULT_REVIEWED = DEFAULT_DIR / "review_packet.reviewed.jsonl"
DEFAULT_STATIC = DEFAULT_DIR / "review_web"


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


class ReviewStore:
    def __init__(self, template: Path, reviewed: Path):
        self.template_path = template
        self.reviewed_path = reviewed
        self.template_rows = read_jsonl(template)
        self.template_by_key = {row["tool_instance_key"]: row for row in self.template_rows}
        if len(self.template_by_key) != len(self.template_rows):
            raise ValueError("template contains duplicate tool instance keys")
        self.lock = threading.RLock()
        self.rows = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if not self.reviewed_path.exists():
            return copy.deepcopy(self.template_rows)
        reviewed = read_jsonl(self.reviewed_path)
        by_key = {row.get("tool_instance_key"): row for row in reviewed}
        if set(by_key) != set(self.template_by_key) or len(reviewed) != len(self.template_rows):
            raise ValueError("reviewed packet keys differ from immutable template")
        ordered = []
        for template in self.template_rows:
            row = by_key[template["tool_instance_key"]]
            expected = payload_hash(template)
            if row.get("candidate_payload_sha256") != expected or payload_hash(row) != expected:
                raise ValueError(f"immutable candidate changed: {template['tool_instance_key']}")
            ordered.append(row)
        return ordered

    @staticmethod
    def _review_started(review: dict[str, Any]) -> bool:
        if review.get("overall_decision") != "PENDING":
            return True
        return any(item.get("decision") != "PENDING" for item in review.get("field_reviews", [])) or any(
            item.get("decision") != "PENDING" for item in review.get("projection_reviews", [])
        ) or bool(str(review.get("reviewer_anonymous_id", "")).strip())

    def state(self, row: dict[str, Any]) -> dict[str, Any]:
        review = row.get("review") or {}
        errors, decision = validate_review(row)
        started = self._review_started(review)
        if not started:
            status = "unreviewed"
        elif errors:
            status = "in_progress"
        elif decision == "approve":
            status = "approved"
        else:
            status = "rejected"
        return {"tool_instance_key": row["tool_instance_key"], "status": status, "errors": errors}

    def states(self) -> list[dict[str, Any]]:
        return [self.state(row) for row in self.rows]

    def progress(self) -> dict[str, int]:
        counts = Counter(item["status"] for item in self.states())
        return {
            "total": len(self.rows),
            "completed": counts["approved"] + counts["rejected"],
            "approved": counts["approved"],
            "rejected": counts["rejected"],
            "in_progress": counts["in_progress"],
            "unreviewed": counts["unreviewed"],
        }

    def bootstrap(self) -> dict[str, Any]:
        with self.lock:
            return {"rows": copy.deepcopy(self.rows), "states": self.states(), "progress": self.progress()}

    def save(self, suite: str, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if set(payload) != {"review"} or not isinstance(payload["review"], dict):
            raise ValueError("request must contain only a review object")
        key = f"{suite}/{tool_name}"
        if key not in self.template_by_key:
            raise KeyError(f"unknown tool instance {key}")
        with self.lock:
            index = next(i for i, row in enumerate(self.rows) if row["tool_instance_key"] == key)
            row = copy.deepcopy(self.rows[index])
            row["review"] = copy.deepcopy(payload["review"])
            if payload_hash(row) != payload_hash(self.template_by_key[key]):
                raise ValueError("immutable candidate content changed")
            self.rows[index] = row
            write_jsonl_atomic(self.reviewed_path, self.rows)
            return {"row": copy.deepcopy(row), "states": self.states(), "progress": self.progress()}

    def validate_all(self) -> dict[str, Any]:
        if not self.reviewed_path.exists():
            return {"status": "awaiting_external_human_review", "n_errors": 1}
        summary, compiled = validate(self.template_path, self.reviewed_path)
        write_outputs(self.template_path.parent, summary, compiled)
        return summary


class Server(ThreadingHTTPServer):
    store: ReviewStore
    static_dir: Path


class Handler(BaseHTTPRequestHandler):
    server: Server

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def json_response(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def serve_static(self, name: str, content_type: str) -> None:
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
            self.serve_static("index.html", "text/html; charset=utf-8")
        elif path == "/app.js":
            self.serve_static("app.js", "text/javascript; charset=utf-8")
        elif path == "/styles.css":
            self.serve_static("styles.css", "text/css; charset=utf-8")
        elif path == "/api/bootstrap":
            self.json_response(self.server.store.bootstrap())
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def read_payload(self) -> dict[str, Any]:
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Content-Type must be application/json")
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2_000_000:
            raise ValueError("invalid request length")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("request body must be an object")
        return payload

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/validate":
                self.json_response(self.server.store.validate_all())
                return
            parts = path.split("/")
            if len(parts) == 5 and parts[1:3] == ["api", "review"]:
                suite, tool_name = unquote(parts[3]), unquote(parts[4])
                self.json_response(self.server.store.save(suite, tool_name, self.read_payload()))
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except KeyError as exc:
            self.json_response({"error": str(exc)}, HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as exc:
            self.json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - defensive server boundary
            self.json_response({"error": f"internal error: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8785)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--reviewed", type=Path, default=DEFAULT_REVIEWED)
    parser.add_argument("--static-dir", type=Path, default=DEFAULT_STATIC)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = Server((args.host, args.port), Handler)
    server.store = ReviewStore(args.template, args.reviewed)
    server.static_dir = args.static_dir
    url = f"http://{args.host}:{args.port}/"
    print(f"E85 review interface: {url}")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
