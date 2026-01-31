#!/usr/bin/env python3
"""Post to agentchan (chan.alphakek.ai) and log it.

Agentchan's current instance appears to require a thumbnailable attachment even
for text posts, so we upload a tiny generated PNG.

Usage examples:
  python3 agentchan_post.py --board dev --resto 51 --com "hello"
  python3 agentchan_post.py --board dev --sub "Title" --com "Thread body"

Logs append to docs/SOCIAL_LOG.md and docs/AGENTCHAN_LOG.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
from pathlib import Path

BASE = "https://chan.alphakek.ai"
POST_ENDPOINT = f"{BASE}/imgboard.php"

REPO_ROOT = Path(__file__).resolve().parent
LOG_SOCIAL = REPO_ROOT / "docs" / "SOCIAL_LOG.md"
LOG_CHAN = REPO_ROOT / "docs" / "AGENTCHAN_LOG.md"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def make_png(path: Path, *, w: int = 256, h: int = 256) -> None:
    """Write a small valid PNG without external deps."""
    import binascii
    import struct
    import zlib

    # RGBA solid dark gray
    row = b"\x00" + (b"\x10\x10\x10\xff" * w)
    raw = row * h
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack("!I", len(data))
            + tag
            + data
            + struct.pack("!I", binascii.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack("!IIBBBBB", w, h, 8, 6, 0, 0, 0)
    out = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    path.write_bytes(out)


def run_curl(form: list[str]) -> str:
    proc = subprocess.run(
        ["curl", "-s", "-i", "-X", "POST", POST_ENDPOINT, *form],
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.stdout + proc.stderr


def parse_redirect_anchor(resp: str) -> str | None:
    """Extract the redirect target from the HTML meta refresh.

    Example snippet:
      <meta http-equiv="refresh" content="2;URL='./dev/res/51.html#p53'">

    Returns:
      dev/res/51.html#p53
    """
    # Common forms:
    #  - URL='./dev/res/51.html#p53'
    #  - URL="./dev/res/51.html#p53"
    #  - URL=./dev/res/51.html#p53
    m = re.search(r"URL=['\"]?\./([^'\"\s>]+)", resp)
    if not m:
        return None
    return m.group(1).strip()


def append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", required=True)
    ap.add_argument("--com", required=True)
    ap.add_argument("--sub")
    ap.add_argument("--resto", type=int)
    args = ap.parse_args()

    tmp_png = Path("/tmp/agentchan_post.png")
    make_png(tmp_png)

    form: list[str] = []
    form += ["-F", "mode=regist"]
    form += ["-F", f"board={args.board}"]
    if args.sub:
        form += ["-F", f"sub={args.sub}"]
    if args.resto is not None:
        form += ["-F", f"resto={args.resto}"]
    # Use $'..' style newlines by passing literal newlines directly in value
    form += ["-F", f"com={args.com}"]
    form += ["-F", f"upfile=@{tmp_png};filename=agentchan.png"]

    resp = run_curl(form)
    anchor = parse_redirect_anchor(resp)

    ts = utc_now()
    if anchor:
        url = f"{BASE}/{anchor}"
        log_line = f"- {ts} agentchan: {url} (board={args.board}{', resto='+str(args.resto) if args.resto else ''}{', sub='+args.sub if args.sub else ''})"
    else:
        # store a short failure marker (but not full response)
        log_line = f"- {ts} agentchan: POST FAILED (board={args.board})"

    append_log(LOG_CHAN, log_line)
    append_log(LOG_SOCIAL, log_line)

    # print the URL (or failure) for CLI visibility
    print(log_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
