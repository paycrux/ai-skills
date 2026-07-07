#!/usr/bin/env python3
"""Fetch Notion page markdown through notion-cli."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


UUID_RE = re.compile(
    r"(?i)([0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12})"
)


def extract_page_id(value: str) -> str | None:
    matches = UUID_RE.findall(value)
    if not matches:
        return None
    raw = matches[-1].replace("-", "").lower()
    if len(raw) != 32:
        return None
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"


def run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def fail(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def write_command_output(command: list[str], output_path: Path, timeout: int) -> None:
    result = run(command, timeout)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "no stderr"
        fail(f"command failed: {' '.join(command)}\n{stderr}", result.returncode)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.stdout, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a Notion page as markdown using notion-cli."
    )
    parser.add_argument("source", help="Notion page URL or page ID")
    parser.add_argument(
        "-o",
        "--output",
        help="Write markdown to this file instead of stdout",
    )
    parser.add_argument(
        "--metadata",
        help="Optional path for page metadata JSON from notion-cli page retrieve",
    )
    parser.add_argument(
        "--children",
        help="Optional path for child block JSON from notion-cli block children",
    )
    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="Run notion-cli whoami before fetching",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Command timeout in seconds",
    )
    args = parser.parse_args()

    cli = shutil.which("notion-cli")
    if not cli:
        fail("notion-cli was not found on PATH")

    if args.check_auth:
        auth = run([cli, "whoami"], args.timeout)
        if auth.returncode != 0:
            stderr = auth.stderr.strip() or auth.stdout.strip() or "no stderr"
            fail(f"notion-cli authentication check failed\n{stderr}", auth.returncode)

    markdown_command = [cli, "markdown", "get", args.source]
    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = run([*markdown_command, "--file", str(output_path)], args.timeout)
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "no stderr"
            fail(f"command failed: {' '.join(markdown_command)}\n{stderr}", result.returncode)
        print(str(output_path))
    else:
        result = run(markdown_command, args.timeout)
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "no stderr"
            fail(f"command failed: {' '.join(markdown_command)}\n{stderr}", result.returncode)
        print(result.stdout, end="")

    page_id = extract_page_id(args.source)
    if (args.metadata or args.children) and not page_id:
        fail("could not extract a page ID for metadata or child block fetch")

    if args.metadata and page_id:
        write_command_output(
            [cli, "page", "retrieve", page_id, "--json"],
            Path(args.metadata).expanduser(),
            args.timeout,
        )

    if args.children and page_id:
        write_command_output(
            [cli, "block", "children", page_id, "--page-all", "--json"],
            Path(args.children).expanduser(),
            args.timeout,
        )


if __name__ == "__main__":
    main()
