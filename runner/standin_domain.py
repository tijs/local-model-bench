"""Synthetic Peixinho domain: a benchmark simulator, never a production backend."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any

SCOPE = "peixinho-standin-v1"
Json = dict[str, Any]


def tool(name: str, description: str, properties: Json, required: list[str]) -> Json:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


STRING = {"type": "string", "minLength": 1}
TOOLS = [
    tool(
        "search_records",
        "Case-insensitive substring search over authorized record IDs, titles and visible content. This is not semantic search; use short queries. Empty query lists all accessible records.",
        {"query": {"type": "string"}},
        ["query"],
    ),
    tool(
        "read_record",
        "Read one authorized record, including saved task progress.",
        {"record_id": STRING},
        ["record_id"],
    ),
    tool(
        "capture",
        "Save one capture. Shopping is family-visible; Inbox is private and pending. Use the supplied operation ID and source ID, one operation per part.",
        {
            "text": STRING,
            "destination": {"type": "string", "enum": ["shopping", "inbox"]},
            "operation_id": STRING,
            "source_id": STRING,
        },
        ["text", "destination", "operation_id", "source_id"],
    ),
    tool(
        "propose_routes",
        "Propose ranked private-note/private-task choices for a pending private Inbox capture. This is not a routing decision or publication.",
        {
            "record_id": STRING,
            "choices": {
                "type": "array",
                "items": {"type": "string", "enum": ["private_note", "private_task"]},
                "minItems": 1,
                "uniqueItems": True,
            },
            "operation_id": STRING,
        },
        ["record_id", "choices", "operation_id"],
    ),
    tool(
        "operation_status",
        "Look up a durable receipt by supplied operation ID after an ambiguous timeout.",
        {"operation_id": STRING},
        ["operation_id"],
    ),
    tool(
        "set_progress",
        "Only explicit Done completes the next incomplete step. Later/Help do not advance. Reopen preserves checks.",
        {
            "record_id": STRING,
            "action": {"type": "string", "enum": ["done", "later", "help", "reopen"]},
            "operation_id": STRING,
        },
        ["record_id", "action", "operation_id"],
    ),
    tool(
        "preview_share",
        "Create a private exact preview of a selected passage for family publication. This is not approval or publication.",
        {"record_id": STRING, "text": STRING, "operation_id": STRING},
        ["record_id", "text", "operation_id"],
    ),
    tool(
        "publish_preview",
        "Publish only a preview explicitly approved by the trusted user event. No model-supplied approval is accepted.",
        {"preview_id": STRING, "operation_id": STRING},
        ["preview_id", "operation_id"],
    ),
    tool(
        "private_copy",
        "Create a separate caller-owned private copy; keep the family original intact.",
        {"record_id": STRING, "operation_id": STRING},
        ["record_id", "operation_id"],
    ),
    tool(
        "set_routine",
        "Set an explicitly requested routine for a task. Days are ISO weekdays 1..7; local time HH:MM. Monthly/interval recurrence is unsupported.",
        {
            "record_id": STRING,
            "days": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1, "maximum": 7},
                "minItems": 1,
                "uniqueItems": True,
            },
            "time": STRING,
            "operation_id": STRING,
        },
        ["record_id", "days", "time", "operation_id"],
    ),
]
SCHEMAS = {t["function"]["name"]: t["function"]["parameters"] for t in TOOLS}
MUTATIONS = {
    "capture",
    "propose_routes",
    "set_progress",
    "preview_share",
    "publish_preview",
    "private_copy",
    "set_routine",
}


class DomainError(ValueError):
    """A rejected model operation; not a broken simulator."""


def validate(schema: Json, value: Any, path: str = "arguments") -> None:
    kind = schema.get("type")
    good = {
        "object": isinstance(value, dict),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "array": isinstance(value, list),
    }
    if kind in good and not good[kind]:
        raise DomainError(f"{path}: expected {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise DomainError(f"{path}: unsupported value")
    if kind == "object":
        if set(value) - set(schema["properties"]):
            raise DomainError(f"{path}: unknown fields")
        if set(schema.get("required", [])) - set(value):
            raise DomainError(f"{path}: missing fields")
        for key, item in value.items():
            validate(schema["properties"][key], item, f"{path}.{key}")
    elif kind == "string" and len(value) < schema.get("minLength", 0):
        raise DomainError(f"{path}: empty value")
    elif kind == "integer" and not schema.get("minimum", value) <= value <= schema.get(
        "maximum", value
    ):
        raise DomainError(f"{path}: out of range")
    elif kind == "array":
        if len(value) < schema.get("minItems", 0) or len(set(map(str, value))) != len(
            value
        ):
            raise DomainError(f"{path}: empty or duplicate items")
        for item in value:
            validate(schema["items"], item, path)


@dataclass
class Domain:
    actor: str
    records: Json
    allowed_operations: list[str]
    source_id: str
    journal: list[Json] = field(default_factory=list)
    receipts: Json = field(default_factory=dict)
    previews: Json = field(default_factory=dict)
    approvals: list[str] = field(default_factory=list)
    occurrences: Json = field(default_factory=dict)
    clock: str = "2026-10-26"
    phase: int = 0
    audience: str = "private"
    selected_passages: Json = field(default_factory=dict)
    fail_after_commit: list[str] = field(default_factory=list)

    def snapshot(self) -> Json:
        return copy.deepcopy(self.__dict__)

    @classmethod
    def restore(cls, state: Json) -> Domain:
        return cls(**copy.deepcopy(state))

    def visible(self, record: Json) -> bool:
        return record.get("visibility") == "family" or (
            record.get("owner") == self.actor
            and (
                self.audience == "private" or record.get("id") in self.selected_passages
            )
        )

    def get(self, record_id: str) -> Json:
        record = self.records.get(record_id)
        if not record or record.get("deleted") or not self.visible(record):
            raise DomainError("record unavailable to this account")
        return record

    def projection(self, record: Json) -> Json:
        if self.audience == "family" and record.get("visibility") == "private":
            return {
                "id": record["id"],
                "title": record["title"],
                "content": self.selected_passages[record["id"]],
                "visibility": "private",
                "owner": self.actor,
            }
        return copy.deepcopy(record)

    def _receipt(self, operation_id: str) -> Json:
        if operation_id not in self.allowed_operations:
            raise DomainError("operation ID is not assigned to this request")
        receipt = self.receipts.get(operation_id, {})
        if receipt:
            if receipt.get("actor") != self.actor:
                raise DomainError("receipt unavailable to this account")
            old = receipt["arguments"]
            if "record_id" in old:
                self.get(old["record_id"])
            if receipt["tool"] == "publish_preview":
                preview = self.previews.get(old["preview_id"])
                if not preview or preview["actor"] != self.actor:
                    raise DomainError("preview unavailable to this account")
                self.get(preview["source"])
        return receipt

    def execute(self, name: str, arguments: Any) -> Json:
        event: Json = {
            "phase": self.phase,
            "actor": self.actor,
            "tool": name,
            "arguments": copy.deepcopy(arguments),
        }
        try:
            if name not in SCHEMAS:
                raise DomainError("unknown tool")
            validate(SCHEMAS[name], arguments)
            # Recheck authorization BEFORE returning a replayed receipt.
            if "record_id" in arguments:
                self.get(arguments["record_id"])
            operation_id = arguments.get("operation_id")
            previous = (
                self._receipt(operation_id)
                if operation_id and name in MUTATIONS
                else {}
            )
            if previous:
                if previous["tool"] != name or previous["arguments"] != arguments:
                    raise DomainError(
                        "operation ID already used for different arguments"
                    )
                result = copy.deepcopy(previous["result"])
                event.update(status="replayed", result=result)
                self.journal.append(event)
                return result
            result = self._apply(name, arguments)
            if name in MUTATIONS:
                self.receipts[operation_id] = {
                    "actor": self.actor,
                    "tool": name,
                    "arguments": copy.deepcopy(arguments),
                    "result": copy.deepcopy(result),
                }
            event.update(status="accepted", result=copy.deepcopy(result))
            self.journal.append(event)
            if operation_id in self.fail_after_commit:
                self.fail_after_commit.remove(operation_id)
                event["response_lost"] = True
                return {
                    "error": "response lost after dispatch; commit outcome unknown; look up operation_status"
                }
            return result
        except DomainError as exc:
            event.update(status="denied", error=str(exc))
            self.journal.append(event)
            return {"error": str(exc)}

    def _apply(self, name: str, args: Json) -> Json:
        if name == "search_records":
            query = args["query"].casefold()
            return {
                "records": [
                    {"id": key, "title": r["title"], "visibility": r["visibility"]}
                    for key, r in self.records.items()
                    if self.visible(r)
                    and not r.get("deleted")
                    and query
                    in (
                        key + " " + r["title"] + " " + self.projection(r).get("content", "")
                    ).casefold()
                ]
            }
        if name == "read_record":
            return self.projection(self.get(args["record_id"]))
        if name == "operation_status":
            if args["operation_id"] not in self.allowed_operations:
                raise DomainError("operation ID is not assigned to this request")
            return {
                "receipt": copy.deepcopy(self._receipt(args["operation_id"])) or None
            }
        if name == "capture":
            if args["source_id"] != self.source_id:
                raise DomainError("source ID does not belong to this request")
            destination = args["destination"]
            key = "capture:" + args["operation_id"]
            self.records[key] = {
                "id": key,
                "title": args["text"],
                "content": args["text"],
                "visibility": "family" if destination == "shopping" else "private",
                "owner": self.actor,
                "destination": destination,
                "source_id": self.source_id,
                "pending": destination == "inbox",
            }
            return {
                "status": "saved" if destination == "shopping" else "pending",
                "record_id": key,
                "visibility": self.records[key]["visibility"],
                "operation_id": args["operation_id"],
            }
        if name == "propose_routes":
            record = self.get(args["record_id"])
            if (
                record.get("destination") != "inbox"
                or not record.get("pending")
                or record["visibility"] != "private"
            ):
                raise DomainError(
                    "routing choices require a private pending Inbox capture"
                )
            record["routing_choices"] = list(args["choices"])
            return {
                "status": "pending",
                "record_id": record["id"],
                "routing_choices": record["routing_choices"],
                "visibility": "private",
            }
        if name == "set_progress":
            record = self.get(args["record_id"])
            if "steps" not in record:
                raise DomainError("record has no steps")
            action = args["action"]
            if action == "done":
                for step in record["steps"]:
                    if not step["done"]:
                        step["done"] = True
                        break
                record["complete"] = all(s["done"] for s in record["steps"])
            elif action == "reopen":
                record["complete"] = False
            record["current_step"] = next(
                (s["id"] for s in record["steps"] if not s["done"]), None
            )
            return copy.deepcopy(record)
        if name == "preview_share":
            self.get(args["record_id"])
            key = "preview:" + args["operation_id"]
            self.previews[key] = {
                "id": key,
                "text": args["text"],
                "source": args["record_id"],
                "actor": self.actor,
            }
            return {
                "preview_id": key,
                "text": args["text"],
                "audience": "family",
                "status": "awaiting explicit user approval",
            }
        if name == "publish_preview":
            preview = self.previews.get(args["preview_id"])
            if (
                not preview
                or preview["actor"] != self.actor
                or args["preview_id"] not in self.approvals
            ):
                raise DomainError("preview has no trusted user approval")
            self.get(preview["source"])
            key = "shared:" + args["operation_id"]
            self.records[key] = {
                "id": key,
                "title": "Shared passage",
                "content": preview["text"],
                "visibility": "family",
                "owner": self.actor,
            }
            self.approvals.remove(args["preview_id"])
            return {"status": "published", "record_id": key, "visibility": "family"}
        if name == "private_copy":
            original = self.get(args["record_id"])
            if original["visibility"] != "family":
                raise DomainError("source is not a family record")
            key = "copy:" + args["operation_id"]
            self.records[key] = {
                "id": key,
                "title": original["title"],
                "content": original["content"],
                "owner": self.actor,
                "visibility": "private",
            }
            return {"record_id": key, "status": "copied", "visibility": "private"}
        if name == "set_routine":
            record = self.get(args["record_id"])
            if "steps" not in record:
                raise DomainError("routine source has no steps")
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", args["time"]):
                raise DomainError("time must be HH:MM")
            record["schedule"] = {"days": sorted(args["days"]), "time": args["time"]}
            return {
                "status": "scheduled",
                "record_id": record["id"],
                "schedule": record["schedule"],
            }
        raise DomainError("unknown operation")

    def advance_day(self, date: str, weekday: int) -> None:
        """Deterministic simulator invariant, not an LLM or notification score."""
        self.clock = date
        for key, record in self.records.items():
            schedule = record.get("schedule")
            if schedule and self.visible(record) and weekday in schedule["days"]:
                occurrence_id = f"{key}:{self.actor}:{date}"
                self.occurrences.setdefault(
                    occurrence_id,
                    {
                        "id": occurrence_id,
                        "owner": self.actor,
                        "steps": [
                            {"id": s["id"], "text": s["text"], "done": False}
                            for s in record["steps"]
                        ],
                        "complete": False,
                    },
                )

    def approve_exact(self, text: str, source_record_id: str) -> list[str]:
        """Only the trusted scripted user calls this; it is absent from TOOLS."""
        matching = [
            key
            for key, p in self.previews.items()
            if p["actor"] == self.actor
            and p["text"] == text
            and p["source"] == source_record_id
        ]
        self.approvals.extend(key for key in matching if key not in self.approvals)
        return matching


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
