import json

from lamp.adapters.inspect_import import convert_file, inspect_records_to_lamp_rows


def test_inspect_records_to_lamp_rows_preserves_metadata_and_behavior_features():
    rows = inspect_records_to_lamp_rows(
        [
            {
                "id": "sample-1",
                "input": "What is 2+2?",
                "output": "I am not sure, maybe 4.",
                "target": "4",
                "scores": {"accuracy": 1},
                "metadata": {"task_id": "math", "condition": "evaluation", "difficulty": 0.2},
            }
        ]
    )

    assert rows[0]["episode_id"] == "sample-1"
    assert rows[0]["task_id"] == "math"
    assert rows[0]["condition"] == "evaluation"
    assert rows[0]["score"] == 1
    assert rows[0]["metadata_difficulty"] == 0.2
    assert rows[0]["visible_uncertainty_cue"] == 1


def test_convert_file_accepts_jsonl(tmp_path):
    source = tmp_path / "inspect.jsonl"
    source.write_text(
        json.dumps({"id": "a", "prompt": "p", "response": "r", "score": 0.5, "label": 1}) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "lamp.csv"

    rows = convert_file(source, output)

    assert len(rows) == 1
    assert output.exists()

