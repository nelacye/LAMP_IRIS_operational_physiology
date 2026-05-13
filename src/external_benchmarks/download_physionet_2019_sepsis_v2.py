#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download PhysioNet/CinC 2019 Challenge .psv files by crawling directory listings.

Why v2 exists:
PhysioNet does not expose training_setA.zip / training_setB.zip at the guessed URL.
The files are available as directory listings:
  https://physionet.org/files/challenge-2019/1.0.0/training/training_setA/
  https://physionet.org/files/challenge-2019/1.0.0/training/training_setB/

Run:
  py .\download_physionet_2019_sepsis_v2.py --out .\real_data\physionet\challenge-2019 --sets A --max-files 1000

All set A:
  py .\download_physionet_2019_sepsis_v2.py --out .\real_data\physionet\challenge-2019 --sets A

Smoke sample:
  py .\download_physionet_2019_sepsis_v2.py --out .\real_data\physionet\challenge-2019 --sets A --max-files 500
"""

from __future__ import annotations

import argparse
import csv
import html.parser
import json
import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


BASE = "https://physionet.org/files/challenge-2019/1.0.0/training/"
SET_URLS = {
    "A": BASE + "training_setA/",
    "B": BASE + "training_setB/",
}


class LinkParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for k, v in attrs:
            if k.lower() == "href":
                self.links.append(v)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--sets", default="A", help="A, B, or A,B")
    p.add_argument("--max-files", type=int, default=0, help="0 = all files")
    p.add_argument("--sleep", type=float, default=0.01)
    p.add_argument("--timeout", type=int, default=60)
    return p.parse_args()


def fetch(url, timeout=60):
    req = Request(url, headers={"User-Agent": "LAMP-sepsis-downloader-v2/0.1"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()


def list_psv_urls(set_url, timeout=60):
    html = fetch(set_url, timeout=timeout).decode("utf-8", errors="ignore")
    parser = LinkParser()
    parser.feed(html)
    urls = []
    for href in parser.links:
        if href.endswith(".psv"):
            urls.append(urljoin(set_url, href))
    return sorted(set(urls))


def download_one(url, dest, timeout=60):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return "exists", dest.stat().st_size
    data = fetch(url, timeout=timeout)
    dest.write_bytes(data)
    return "downloaded", len(data)


def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    manifest = []

    for s in [x.strip().upper() for x in args.sets.split(",") if x.strip()]:
        if s not in SET_URLS:
            raise ValueError("Use --sets A, --sets B, or --sets A,B")
        set_url = SET_URLS[s]
        urls = list_psv_urls(set_url, timeout=args.timeout)
        if args.max_files and len(urls) > args.max_files:
            urls = urls[:args.max_files]

        set_dir = out / "training" / f"training_set{s}"
        set_dir.mkdir(parents=True, exist_ok=True)

        print(f"Set {s}: discovered/downloading {len(urls)} .psv files")
        for i, url in enumerate(urls, 1):
            name = url.rstrip("/").split("/")[-1]
            dest = set_dir / name
            try:
                status, nbytes = download_one(url, dest, timeout=args.timeout)
            except Exception as e:
                status, nbytes = "error", 0
                print(f"ERROR {name}: {e}")
            rows.append({"set": s, "index": i, "url": url, "dest": str(dest), "status": status, "bytes": nbytes})
            if i % 500 == 0:
                print(f"  {i}/{len(urls)}")
            time.sleep(args.sleep)

        manifest.append({"set": s, "set_url": set_url, "n_files": len(urls), "set_dir": str(set_dir)})

    with (out / "download_manifest_v2.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    with (out / "download_log_v2.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["set", "index", "url", "dest", "status", "bytes"])
        w.writeheader()
        w.writerows(rows)

    print(json.dumps({
        "out": str(out),
        "manifest": str(out / "download_manifest_v2.json"),
        "log": str(out / "download_log_v2.csv"),
        "downloaded_or_existing": sum(1 for r in rows if r["status"] in ["downloaded", "exists"]),
        "errors": sum(1 for r in rows if r["status"] == "error"),
    }, indent=2))


if __name__ == "__main__":
    main()
