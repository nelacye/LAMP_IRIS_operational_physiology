"""Import simple Inspect AI JSON/JSONL exports into the LAMP table schema.

The adapter intentionally avoids depending on Inspect internals. It accepts a
common exported-record shape: JSONL rows, a JSON list, or a JSON object with a
`samples`, `records`, `events`, or `data` list. Unknown metadata is preserved
under `metadata_*` columns when scalar.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


SCALAR_TYPES = (str, int, float, bool, type(None))


def load_inspect_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    payload = json.loads(text)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("samples", "records", "events", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    raise ValueError(f"Unsupported Inspect export payload: {path}")


def inspect_records_to_lamp_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        metadata = _as_dict(record.get("metadata"))
        scores = _as_dict(record.get("scores"))
        row: dict[str, Any] = {
            "episode_id": str(_first(record, metadata, ["episode_id", "sample_id", "id"], default=f"inspect_{idx:06d}")),
            "task_id": str(_first(record, metadata, ["task_id", "task", "dataset"], default="inspect_task")),
            "prompt": _prompt_text(record),
            "response": _response_text(record),
            "score": _score_value(record, scores),
            "label": _label_value(record, metadata),
            "model": str(_first(record, metadata, ["model", "model_name"], default="unknown")),
            "condition": str(_first(record, metadata, ["condition", "split", "framing"], default="unknown")),
            "timestamp": _first(record, metadata, ["timestamp", "time"], default=idx),
            "order": idx,
        }
        row.update(_visible_behavior_features(row["response"]))
        row.update(_flatten_metadata(metadata))
        row.update(_flatten_scores(scores))
        rows.append(row)
    return rows


def write_lamp_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = sorted({key for row in rows for key in row})
    preferred = [
        "episode_id",
        "task_id",
        "prompt",
        "response",
        "score",
        "label",
        "model",
        "condition",
        "timestamp",
        "order",
    ]
    columns = preferred + [col for col in columns if col not in preferred]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def convert_file(input_path: Path, output_path: Path) -> list[dict[str, Any]]:
    rows = inspect_records_to_lamp_rows(load_inspect_records(input_path))
    write_lamp_csv(rows, output_path)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert Inspect JSON/JSONL export to LAMP CSV.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    rows = convert_file(args.input, args.output)
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, indent=2))
    return 0


def _prompt_text(record: dict[str, Any]) -> str:
    for key in ("prompt", "input", "question"):
        value = record.get(key)
        if isinstance(value, str):
            return value
    messages = record.get("messages") or record.get("conversation")
    if isinstance(messages, list):
        return "\n".join(
            str(item.get("content", item))
            for item in messages
            if isinstance(item, (dict, str))
        )
    return ""


def _response_text(record: dict[str, Any]) -> str:
    for key in ("response", "output", "completion", "answer"):
        value = record.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            text = value.get("completion") or value.get("content") or value.get("text")
            if isinstance(text, str):
                return text
    return ""


def _score_value(record: dict[str, Any], scores: dict[str, Any]) -> Any:
    for key in ("score", "value"):
        if key in record and isinstance(record[key], SCALAR_TYPES):
            return record[key]
    for key in ("score", "accuracy", "correct", "value"):
        if key in scores and isinstance(scores[key], SCALAR_TYPES):
            return scores[key]
    return ""


def _label_value(record: dict[str, Any], metadata: dict[str, Any]) -> Any:
    for key in ("label", "target", "ideal", "answer_key"):
        value = record.get(key, metadata.get(key))
        if isinstance(value, SCALAR_TYPES):
            return value
    return ""


def _first(
    record: dict[str, Any],
    metadata: dict[str, Any],
    keys: list[str],
    *,
    default: Any,
) -> Any:
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
        if key in metadata and metadata[key] is not None:
            return metadata[key]
    return default


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _visible_behavior_features(response: str) -> dict[str, Any]:
    lowered = response.lower()
    return {
        "visible_response_length": len(response),
        "visible_refusal_cue": int(any(token in lowered for token in ["cannot", "can't", "unable", "not able"])),
        "visible_uncertainty_cue": int(any(token in lowered for token in ["unsure", "not sure", "maybe", "uncertain"])),
    }


def _flatten_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        f"metadata_{key}": value
        for key, value in metadata.items()
        if isinstance(value, SCALAR_TYPES)
    }


def _flatten_scores(scores: dict[str, Any]) -> dict[str, Any]:
    return {
        f"score_{key}": value
        for key, value in scores.items()
        if isinstance(value, SCALAR_TYPES)
    }


if __name__ == "__main__":
    raise SystemExit(main())
