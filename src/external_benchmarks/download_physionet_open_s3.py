#!/usr/bin/env python3
"""Download open PhysioNet files from the public S3 mirror.

This is useful for resources with many small files, where crawling the HTML
directory listing is slow. It writes an aria2 input file with only missing files
and uses aria2c when available.

Examples:
  python src/external_benchmarks/download_physionet_open_s3.py \
    --prefix challenge-2019/1.0.0/training/training_setA/ \
    --out real_data/physionet/challenge-2019/training/training_setA

  python src/external_benchmarks/download_physionet_open_s3.py \
    --prefix vitaldb-arrhythmia/1.0.0/ \
    --out real_data/vitaldb-arrhythmia-1.0.0
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


S3_ROOT = "https://physionet-open.s3.amazonaws.com/"
S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True, help="S3 key prefix under physionet-open")
    parser.add_argument("--out", required=True, help="Local output directory")
    parser.add_argument("--max-files", type=int, default=0, help="0 = all listed files")
    parser.add_argument("--aria2-workers", type=int, default=64)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    return parser.parse_args()


def list_objects(prefix: str, timeout: int) -> list[dict[str, object]]:
    token = None
    objects: list[dict[str, object]] = []
    while True:
        url = (
            S3_ROOT
            + "?list-type=2&max-keys=1000&prefix="
            + quote(prefix, safe="/")
        )
        if token:
            url += "&continuation-token=" + quote(token, safe="")
        request = Request(url, headers={"User-Agent": "LAMP-physionet-s3/0.1"})
        with urlopen(request, timeout=timeout) as handle:
            root = ET.fromstring(handle.read())
        for contents in root.findall("s3:Contents", S3_NS):
            key = contents.findtext("s3:Key", namespaces=S3_NS)
            size = int(contents.findtext("s3:Size", default="0", namespaces=S3_NS))
            if key and not key.endswith("/"):
                objects.append({"key": key, "size": size})
        truncated = root.findtext("s3:IsTruncated", default="false", namespaces=S3_NS)
        if truncated != "true":
            return objects
        token = root.findtext("s3:NextContinuationToken", namespaces=S3_NS)
        if not token:
            raise RuntimeError("S3 response was truncated but did not include a continuation token")


def build_aria2_input(
    objects: list[dict[str, object]],
    prefix: str,
    out_dir: Path,
    max_files: int,
) -> tuple[Path, list[dict[str, object]]]:
    rows = []
    lines = []
    limited = objects[:max_files] if max_files else objects
    for obj in limited:
        key = str(obj["key"])
        size = int(obj["size"])
        rel = key.removeprefix(prefix)
        local = out_dir / rel
        exists = local.exists() and local.stat().st_size == size
        rows.append(
            {
                "key": key,
                "size": size,
                "relative_path": rel,
                "local_path": str(local),
                "exists": exists,
            }
        )
        if not exists:
            lines.extend(
                [
                    S3_ROOT + key,
                    f"  dir={local.parent.as_posix()}",
                    f"  out={local.name}",
                ]
            )

    control_dir = out_dir / ".download"
    control_dir.mkdir(parents=True, exist_ok=True)
    aria2_input = control_dir / "aria2_missing.txt"
    aria2_input.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return aria2_input, rows


def run_aria2(aria2_input: Path, workers: int) -> None:
    if aria2_input.stat().st_size == 0:
        print("No missing files.")
        return
    aria2 = shutil.which("aria2c")
    if not aria2:
        raise RuntimeError("aria2c was not found on PATH; install aria2 or rerun after adding it to PATH")
    command = [
        aria2,
        "-i",
        str(aria2_input),
        "-j",
        str(workers),
        "-x",
        "4",
        "-s",
        "4",
        "--continue=true",
        "--auto-file-renaming=false",
        "--allow-overwrite=true",
        "--max-tries=5",
        "--retry-wait=3",
        "--summary-interval=30",
        "--download-result=hide",
        "--console-log-level=warn",
    ]
    print("Running " + " ".join(command))
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"aria2c failed with exit code {completed.returncode}")


def main() -> int:
    args = parse_args()
    prefix = args.prefix if args.prefix.endswith("/") else args.prefix + "/"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    objects = list_objects(prefix, timeout=args.timeout)
    aria2_input, rows = build_aria2_input(
        objects=objects,
        prefix=prefix,
        out_dir=out_dir,
        max_files=args.max_files,
    )
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "s3_root": S3_ROOT,
        "prefix": prefix,
        "out_dir": str(out_dir),
        "n_listed": len(objects),
        "n_considered": len(rows),
        "n_existing": sum(1 for row in rows if row["exists"]),
        "n_missing_before_download": sum(1 for row in rows if not row["exists"]),
        "bytes_considered": sum(int(row["size"]) for row in rows),
        "aria2_input": str(aria2_input),
    }
    manifest_path = out_dir / ".download" / "s3_download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))

    if not args.dry_run:
        run_aria2(aria2_input, workers=args.aria2_workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
