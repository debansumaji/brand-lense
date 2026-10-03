"""Fetch a URL and print extracted text or complete diagnostic details."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scraper import fetch_product_text


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <url>", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    url = sys.argv[1]
    try:
        text, chars_used = fetch_product_text(url)
    except Exception as exc:  # noqa: BLE001 - this tool is for full diagnostics.
        print(f"exception_type: {type(exc).__name__}", file=sys.stderr)
        print(f"exception_message: {exc}", file=sys.stderr)
        if hasattr(exc, "code"):
            print(f"error_code: {exc.code}", file=sys.stderr)
            print(f"http_status: {exc.status}", file=sys.stderr)
        print("traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    print(f"extracted_chars: {chars_used}")
    print(text[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
