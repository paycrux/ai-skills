#!/usr/bin/env python3
"""Fetch Notion page markdown through notion-cli (npm package @coastal-programs/notion-cli).

The official Notion CLI (Homebrew cask `notion-cli`, binary `ntn`) is a different tool with other
commands; this script cannot use it. Exit codes the calling skill acts on:
    3  notion-cli missing or not the expected tool — run the printed `install:` command
    4  notion-cli not logged in — the user runs the printed `login:` command
"""

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
PACKAGE = "@coastal-programs/notion-cli"
INSTALL_CMD = f"npm i -g {PACKAGE}"
LOGIN_CMD = "notion-cli auth login"
EXIT_INSTALL = 3
EXIT_LOGIN = 4
SIGNED_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\((https?://[^)\s]*X-Amz-[^)\s]*)\)")


def extract_page_id(value: str) -> str | None:
    path = re.split(r"[?#]", value, maxsplit=1)[0]
    matches = UUID_RE.findall(path) or UUID_RE.findall(value)
    if not matches:
        return None
    raw = matches[-1].replace("-", "").lower()
    if len(raw) != 32:
        return None
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"


def strip_signed_images(markdown: str) -> str:
    return SIGNED_IMAGE_RE.sub(
        lambda m: f"![{m.group(1) or 'image'}](notion-image)", markdown
    )


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


def need_install(reason: str) -> None:
    print(f"error: {reason}\ninstall: {INSTALL_CMD}", file=sys.stderr)
    sys.exit(EXIT_INSTALL)


def find_cli(timeout: int) -> str:
    """The notion-cli this script can drive, told apart by the command it needs — never by name alone."""
    cli = shutil.which("notion-cli")
    if not cli:
        if shutil.which("ntn"):
            need_install(f"only the official Notion CLI (ntn) is installed; this skill needs {PACKAGE}, a different tool")
        need_install(f"notion-cli ({PACKAGE}) is not installed")
    probe = run([cli, "markdown", "get", "--help"], timeout)
    if probe.returncode != 0:
        need_install(f"{cli} is not {PACKAGE} (it has no `markdown get` command)")
    return cli


def check_login(cli: str, timeout: int) -> None:
    auth = run([cli, "whoami"], timeout)
    if auth.returncode != 0:
        stderr = auth.stderr.strip() or auth.stdout.strip() or "no stderr"
        print(f"error: notion-cli is not logged in\n{stderr}\nlogin: {LOGIN_CMD}", file=sys.stderr)
        sys.exit(EXIT_LOGIN)


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
    parser.add_argument("source", nargs="?", help="Notion page URL or page ID")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check that notion-cli is installed and logged in; fetch nothing",
    )
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
        "--keep-image-urls",
        action="store_true",
        help="Keep signed S3 image URLs instead of replacing them with a placeholder",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Command timeout in seconds",
    )
    args = parser.parse_args()

    cli = find_cli(args.timeout)
    if args.check or args.check_auth:
        check_login(cli, args.timeout)
    if args.check:
        print("ok: notion-cli installed and logged in")
        return
    if not args.source:
        parser.error("source is required unless --check is given")

    page_id = extract_page_id(args.source)
    markdown_command = [cli, "markdown", "get", page_id or args.source]
    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = run([*markdown_command, "--file", str(output_path)], args.timeout)
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "no stderr"
            fail(f"command failed: {' '.join(markdown_command)}\n{stderr}", result.returncode)
        if not args.keep_image_urls:
            text = output_path.read_text(encoding="utf-8")
            output_path.write_text(strip_signed_images(text), encoding="utf-8")
        print(str(output_path))
    else:
        result = run(markdown_command, args.timeout)
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "no stderr"
            fail(f"command failed: {' '.join(markdown_command)}\n{stderr}", result.returncode)
        print(
            result.stdout if args.keep_image_urls else strip_signed_images(result.stdout),
            end="",
        )

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
