from __future__ import annotations

import csv
import json
import math
from collections.abc import Iterator
from pathlib import Path

from route_planner.models import Delivery, Rejection

FIELDS = ("id", "area", "priority", "weight_kg")


def load_deliveries(path: str | Path) -> tuple[list[Delivery], list[Rejection]]:
    """Read deliveries from a .csv or .json file, returning the valid ones and the rejected ones."""
    path = Path(path)
    reader = _READERS.get(path.suffix.lower())
    if reader is None:
        supported = ", ".join(sorted(_READERS))
        raise ValueError(f"unsupported input format '{path.suffix}'; expected one of: {supported}")

    deliveries: list[Delivery] = []
    rejections: list[Rejection] = []
    seen_ids: set[str] = set()

    for source, record in reader(path):
        parsed = _parse_record(record, source, seen_ids)
        if isinstance(parsed, Rejection):
            rejections.append(parsed)
        else:
            deliveries.append(parsed)

    return deliveries, rejections


def _read_csv(path: Path) -> Iterator[tuple[str, object]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return
        for line_number, row in enumerate(reader, start=2):
            yield f"row {line_number}", row


def _read_json(path: Path) -> Iterator[tuple[str, object]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected a JSON array of delivery objects")
    for index, record in enumerate(payload, start=1):
        yield f"item {index}", record


_READERS = {".csv": _read_csv, ".json": _read_json}


def _parse_record(record: object, source: str, seen_ids: set[str]) -> Delivery | Rejection:
    if not isinstance(record, dict):
        return Rejection("malformed record", source, "expected an object with delivery fields")

    values: dict[str, object] = {}
    for field_name in FIELDS:
        value = record.get(field_name)
        if isinstance(value, str):
            value = value.strip()
        if value is None or value == "":
            return Rejection("missing field", source, f"'{field_name}' is empty or absent")
        values[field_name] = value

    delivery_id = str(values["id"])
    if delivery_id in seen_ids:
        return Rejection("duplicate id", source, f"delivery '{delivery_id}' already seen")

    priority = _parse_priority(values["priority"])
    if priority is None:
        return Rejection(
            "invalid priority", source, f"'{values['priority']}' is not a whole number >= 1"
        )

    weight_kg = _parse_weight(values["weight_kg"])
    if weight_kg is None:
        return Rejection(
            "invalid weight", source, f"'{values['weight_kg']}' is not a weight above 0 kg"
        )

    seen_ids.add(delivery_id)
    return Delivery(delivery_id, str(values["area"]), priority, weight_kg)


def _parse_priority(value: object) -> int | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not number.is_integer() or number < 1:
        return None
    return int(number)


def _parse_weight(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number
