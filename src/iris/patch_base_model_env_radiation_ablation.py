#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Environment-based radiation ablation patch for antarctic_cv_reserve_model_realdata_v2.py.

The previous ablation was not valid because stress_protocol.csv was unchanged.
This patch modifies the BASE MODEL so it reads:
  IRIS_RADIATION_SCALE
  IRIS_RADIATION_SHUFFLE

and applies them directly to stress_protocol['radiation'] before stress_protocol.csv
is written.

Run:
  py .\patch_base_model_env_radiation_ablation.py --base-model .\antarctic_cv_reserve_model_realdata_v2.py
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


PATCH_BLOCK = [
    "",
    "# --- IRIS radiation ablation patch: environment-controlled ---",
    "try:",
    "    _iris_rad_scale = float(os.environ.get('IRIS_RADIATION_SCALE', getattr(args, 'radiation_scale', 1.0)))",
    "except Exception:",
    "    _iris_rad_scale = 1.0",
    "try:",
    "    _iris_rad_shuffle = str(os.environ.get('IRIS_RADIATION_SHUFFLE', getattr(args, 'radiation_shuffle', False))).lower() in ('1', 'true', 'yes', 'y')",
    "except Exception:",
    "    _iris_rad_shuffle = False",
    "if 'radiation' in stress_protocol.columns:",
    "    stress_protocol = stress_protocol.copy()",
    "    stress_protocol['radiation'] = stress_protocol['radiation'] * _iris_rad_scale",
    "    if _iris_rad_shuffle:",
    "        stress_protocol['radiation'] = stress_protocol['radiation'].sample(",
    "            frac=1.0, random_state=int(getattr(args, 'seed', 42))",
    "        ).to_numpy()",
    "# --- end IRIS radiation ablation patch ---",
    "",
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-model", required=True)
    return p.parse_args()


def add_import_os(text: str):
    if re.search(r"^import os\b", text, flags=re.MULTILINE):
        return text, False
    lines = text.splitlines()
    idx = None
    for i, line in enumerate(lines):
        if line.startswith("from __future__ import"):
            idx = i + 1
    if idx is None:
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                idx = i
                break
    if idx is None:
        idx = 0
    lines.insert(idx, "import os")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True


def add_parser_args(text: str):
    changed = False
    if "--radiation-scale" not in text:
        lines = text.splitlines()
        insert_idx = None
        for i, line in enumerate(lines):
            if "add_argument" in line and "--seed" in line:
                insert_idx = i + 1
        if insert_idx is None:
            for i, line in enumerate(lines):
                if "add_argument" in line and "--n" in line:
                    insert_idx = i + 1
        if insert_idx is not None:
            indent = re.match(r"^(\s*)", lines[insert_idx - 1]).group(1)
            parser_name = "p" if "p.add_argument" in lines[insert_idx - 1] else "parser"
            lines.insert(insert_idx, indent + f'{parser_name}.add_argument("--radiation-scale", type=float, default=1.0)')
            text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
            changed = True
    if "--radiation-shuffle" not in text:
        lines = text.splitlines()
        insert_idx = None
        for i, line in enumerate(lines):
            if "--radiation-scale" in line and "add_argument" in line:
                insert_idx = i + 1
        if insert_idx is not None:
            indent = re.match(r"^(\s*)", lines[insert_idx - 1]).group(1)
            parser_name = "p" if "p.add_argument" in lines[insert_idx - 1] else "parser"
            lines.insert(insert_idx, indent + f'{parser_name}.add_argument("--radiation-shuffle", action="store_true")')
            text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
            changed = True
    return text, changed


def patch_before_stress_protocol_to_csv(text: str):
    if "IRIS radiation ablation patch: environment-controlled" in text:
        return text, False

    lines = text.splitlines()
    target_idx = None
    for i, line in enumerate(lines):
        if "stress_protocol.to_csv" in line:
            target_idx = i
            break
    if target_idx is None:
        for i, line in enumerate(lines):
            if ".to_csv" in line and "stress_protocol" in line:
                target_idx = i
                break
    if target_idx is None:
        raise RuntimeError("Could not find stress_protocol.to_csv insertion point.")

    indent = re.match(r"^(\s*)", lines[target_idx]).group(1)
    block = [indent + x if x else "" for x in PATCH_BLOCK]
    lines[target_idx:target_idx] = block
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True


def main():
    args = parse_args()
    path = Path(args.base_model)
    if not path.exists():
        raise FileNotFoundError(path)

    original = path.read_text(encoding="utf-8", errors="ignore")
    backup = path.with_suffix(path.suffix + ".bak_env_radiation_patch")
    if not backup.exists():
        shutil.copy2(path, backup)

    text, os_changed = add_import_os(original)
    text, parser_changed = add_parser_args(text)
    text, patch_changed = patch_before_stress_protocol_to_csv(text)

    path.write_text(text, encoding="utf-8")

    print(json.dumps({
        "base_model": str(path),
        "backup": str(backup),
        "added_import_os": os_changed,
        "added_parser_args": parser_changed,
        "inserted_env_radiation_patch": patch_changed,
        "next": "Run env ablation runner and verify stress_protocol radiation differs across arms."
    }, indent=2))


if __name__ == "__main__":
    main()
