"""Held-out fixture variants/oracles. Never exposed to the agent or its program."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from automation_tasks import visible_input


def variants(task_id: str, partition: str) -> list[str]:
    if partition not in ("development", "heldout"):
        raise ValueError("unknown partition")
    heldout = partition == "heldout"
    if task_id == "shopping-csv":
        return [
            visible_input(task_id, partition),
            "item,quantity\n",
            (
                'item,quantity\n"  Café   beans ",2\nCAFÉ beans,\n"salt, fine",0\n ,9\n'
                if not heldout
                else 'item,quantity\n"  Thé   vert ",3\nTHÉ vert,\n"pepper, black",0\n ,4\n'
            ),
            (
                'item,quantity\nZucchini,0\n zucchini ,7\n"a  b",1\nA B,2\nStraße,1\nSTRASSE,2\n'
                if not heldout
                else 'item,quantity\nPeas,0\n peas ,9\n"x  y",2\nX Y,4\nMaße,2\nMASSE,3\n'
            ),
        ]
    if task_id == "expense-summary":
        return [
            visible_input(task_id, partition),
            "category,amount,status\n",
            (
                'category,amount,status\nFood,0.105, paid \nFOOD,-0.105,PAID\n ,1.005,paid\n"café, outing",2.675,paid\nOther,999.00,void\n'
                if not heldout
                else 'category,amount,status\nBooks,0.115, paid \nBOOKS,-0.115,PAID\n ,3.005,paid\n"thé, outing",1.225,paid\nOther,500.00,void\n'
            ),
            (
                "category,amount,status\na,0.10,paid\na,0.20,paid\nb,-0.005,paid\nB,0.005,paid\n"
                if not heldout
                else "category,amount,status\nx,0.20,paid\nx,0.40,paid\ny,-0.015,paid\nY,0.015,paid\n"
            ),
        ]
    if task_id == "reminder-repair":

        def encode(data):
            if heldout:
                cutoff = datetime.fromisoformat(data["as_of"])
                data["as_of"] = cutoff.replace(year=cutoff.year + 2).isoformat()
                for row in data["reminders"]:
                    row["id"] = "held-" + row["id"]
                    row["title"] = "Held-out " + row["title"]
                    if row.get("due"):
                        due = datetime.fromisoformat(row["due"])
                        row["due"] = due.replace(year=due.year + 2).isoformat()
            return json.dumps(data)

        return [
            visible_input(task_id, partition),
            encode({"as_of": "2026-10-29T10:00:00Z", "reminders": []}),
            encode(
                {
                    "as_of": "2026-10-29T10:00:00+00:00",
                    "reminders": [
                        {
                            "id": "z",
                            "title": 'Keep ü, "quotes" and \\slashes',
                            "due": "2026-10-29T12:00:00+02:00",
                            "completed": False,
                        },
                        {
                            "id": "a",
                            "title": "Same instant",
                            "due": "2026-10-29T05:00:00-05:00",
                            "completed": False,
                        },
                        {
                            "id": "naive",
                            "title": "Skip",
                            "due": "2026-10-28T10:00:00",
                            "completed": False,
                        },
                        {
                            "id": "none",
                            "title": "Skip",
                            "due": None,
                            "completed": False,
                        },
                        {"id": "missing", "title": "Skip", "completed": False},
                        {
                            "id": "future",
                            "title": "Skip",
                            "due": "2026-10-29T10:00:01Z",
                            "completed": False,
                        },
                    ],
                }
            ),
            encode(
                {
                    "as_of": "2026-01-01T00:00:00Z",
                    "reminders": [
                        {
                            "id": "boundary",
                            "title": "New year",
                            "due": "2025-12-31T19:00:00-05:00",
                            "completed": False,
                        },
                        {
                            "id": "done",
                            "title": "Skip",
                            "due": "2025-12-31T00:00:00Z",
                            "completed": True,
                        },
                    ],
                }
            ),
        ]
    raise ValueError("unknown task")


def expected(task_id: str, text: str) -> Any:
    if task_id == "shopping-csv":
        sums: dict[str, int] = {}
        for row in csv.DictReader(io.StringIO(text)):
            name = " ".join(row["item"].split()).casefold()
            if name:
                sums[name] = sums.get(name, 0) + int(row["quantity"].strip() or "1")
        return [{"item": k, "quantity": v} for k, v in sorted(sums.items())]
    if task_id == "expense-summary":
        amounts: dict[str, Decimal] = {}
        for row in csv.DictReader(io.StringIO(text)):
            if row["status"].strip().casefold() == "paid":
                name = " ".join(row["category"].split()).casefold() or "uncategorized"
                amounts[name] = amounts.get(name, Decimal(0)) + Decimal(
                    row["amount"]
                ).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        return {
            "categories": [
                {"category": k, "total": format(v, ".2f")}
                for k, v in sorted(amounts.items())
            ],
            "total": format(sum(amounts.values(), Decimal(0)), ".2f"),
        }
    if task_id == "reminder-repair":
        data = json.loads(text)
        cutoff = datetime.fromisoformat(data["as_of"])
        found = []
        for row in data["reminders"]:
            if row["completed"] or not row.get("due"):
                continue
            due = datetime.fromisoformat(row["due"])
            if due.tzinfo is not None and due <= cutoff:
                found.append(
                    (
                        due,
                        row["id"],
                        {
                            "id": row["id"],
                            "title": row["title"],
                            "due_utc": due.astimezone(UTC).strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                        },
                    )
                )
        return [r for _, _, r in sorted(found)]
    raise ValueError("unknown task")
