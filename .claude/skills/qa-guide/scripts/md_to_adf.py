#!/usr/bin/env python3
"""Convert a markdown section to Atlassian Document Format (ADF) JSON.

Built for /qa-guide: extracts the `## QA 가이드` section from tasks.md and emits ADF
suitable for `acli jira workitem edit --description-file`.

Deliberately never emits taskList/taskItem nodes — a `- [ ]` line becomes a plain
bullet whose text starts with `[ ]`.

Usage:
    python3 md_to_adf.py <input.md> [-o out.json] [--section "## QA 가이드"]
    cat doc.md | python3 md_to_adf.py - -o out.json
"""

import argparse
import json
import re
import sys

# ── inline marks ────────────────────────────────────────────────────────────
# Order matters: code is matched first so its contents are never re-parsed.
INLINE_PATTERNS = [
    ("code", re.compile(r"`([^`]+)`")),
    ("link", re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")),
    ("strong", re.compile(r"\*\*([^*]+)\*\*")),
    ("em", re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")),
    ("strike", re.compile(r"~~([^~]+)~~")),
]


def _text_node(text, marks=None):
    node = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def parse_inline(text, marks=None):
    """Return a list of ADF inline nodes for one line of markdown."""
    marks = marks or []
    if not text:
        return []

    best = None  # (start, name, match)
    for name, pattern in INLINE_PATTERNS:
        m = pattern.search(text)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), name, m)

    if best is None:
        return [_text_node(text, marks)] if text else []

    _, name, m = best
    nodes = []
    if m.start() > 0:
        nodes.extend(parse_inline(text[: m.start()], marks))

    if name == "code":
        # No nested marks inside code spans.
        nodes.append(_text_node(m.group(1), marks + [{"type": "code"}]))
    elif name == "link":
        label = m.group(1) or m.group(2)
        nodes.append(_text_node(label, marks + [{"type": "link", "attrs": {"href": m.group(2)}}]))
    else:
        nodes.extend(parse_inline(m.group(1), marks + [{"type": name}]))

    if m.end() < len(text):
        nodes.extend(parse_inline(text[m.end():], marks))
    return nodes


def paragraph(text):
    # content is always present, empty list included — an empty table cell still needs a
    # paragraph node, and Atlassian serializes empty paragraphs as "content": [].
    return {"type": "paragraph", "content": parse_inline(text.strip())}


# ── block parsing ───────────────────────────────────────────────────────────
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)$")
ORDERED_RE = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
RULE_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
FENCE_RE = re.compile(r"^\s*```(\w*)\s*$")


def split_table_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def cell(text, header):
    node = {"type": "tableHeader" if header else "tableCell", "attrs": {}}
    node["content"] = [paragraph(text)]
    return node


def convert(lines):
    blocks = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        fence = FENCE_RE.match(line)
        if fence:
            lang = fence.group(1)
            opened_at = i + 1  # 1-indexed, for the error message
            i += 1
            body = []
            while i < n and not FENCE_RE.match(lines[i]):
                body.append(lines[i])
                i += 1
            if i >= n:
                # Without this the rest of the document — headings, tables, lists —
                # becomes code-block body and disappears from the ADF with no error.
                sys.exit(
                    "unclosed code fence opened at line %d; everything after it would be "
                    "swallowed into the code block. Close the fence and re-run." % opened_at
                )
            i += 1  # closing fence
            node = {"type": "codeBlock"}
            if lang:
                node["attrs"] = {"language": lang}
            if body:
                # Guarded on purpose: an ADF text node with an empty string is invalid,
                # so an empty code block must carry no content at all.
                node["content"] = [{"type": "text", "text": "\n".join(body)}]
            blocks.append(node)
            continue

        if RULE_RE.match(line):
            blocks.append({"type": "rule"})
            i += 1
            continue

        h = HEADING_RE.match(line)
        if h:
            level = min(len(h.group(1)), 6)
            blocks.append({
                "type": "heading",
                "attrs": {"level": level},
                "content": parse_inline(h.group(2).strip()),
            })
            i += 1
            continue

        # table: a header row followed by a separator row
        if "|" in line and i + 1 < n and TABLE_SEP_RE.match(lines[i + 1]):
            header = split_table_row(line)
            rows = [{"type": "tableRow", "content": [cell(c, True) for c in header]}]
            i += 2
            while i < n and "|" in lines[i] and lines[i].strip():
                cells = split_table_row(lines[i])
                # pad or trim to the header width so the table stays rectangular
                cells = (cells + [""] * len(header))[: len(header)]
                rows.append({"type": "tableRow", "content": [cell(c, False) for c in cells]})
                i += 1
            blocks.append({
                "type": "table",
                "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
                "content": rows,
            })
            continue

        if BULLET_RE.match(line) or ORDERED_RE.match(line):
            block, i = parse_list(lines, i)
            blocks.append(block)
            continue

        # paragraph: consume until a blank line or a line that starts another block
        buf = [line.strip()]
        i += 1
        while i < n and lines[i].strip():
            nxt = lines[i]
            if (HEADING_RE.match(nxt) or BULLET_RE.match(nxt) or ORDERED_RE.match(nxt)
                    or RULE_RE.match(nxt) or FENCE_RE.match(nxt) or "|" in nxt):
                break
            buf.append(nxt.strip())
            i += 1
        blocks.append(paragraph(" ".join(buf)))

    return blocks


def parse_list(lines, start):
    """Parse one list (possibly nested) starting at lines[start]."""
    first = BULLET_RE.match(lines[start]) or ORDERED_RE.match(lines[start])
    base_indent = len(first.group(1))
    ordered = ORDERED_RE.match(lines[start]) is not None and BULLET_RE.match(lines[start]) is None

    items = []
    i = start
    n = len(lines)

    while i < n:
        line = lines[i]
        if not line.strip():
            # a blank line ends the list unless the next line continues it
            if i + 1 < n and (BULLET_RE.match(lines[i + 1]) or ORDERED_RE.match(lines[i + 1])):
                nxt = BULLET_RE.match(lines[i + 1]) or ORDERED_RE.match(lines[i + 1])
                if len(nxt.group(1)) >= base_indent:
                    i += 1
                    continue
            break

        m = BULLET_RE.match(line) or ORDERED_RE.match(line)
        if not m:
            break
        indent = len(m.group(1))
        if indent < base_indent:
            break
        if indent > base_indent:
            # nested list — attach to the previous item
            child, i = parse_list(lines, i)
            if items:
                items[-1]["content"].append(child)
            continue

        text = m.group(2).strip()
        # checkbox lines become plain bullets; ADF taskItem is never emitted
        text = re.sub(r"^\[([ xX])\]\s*", lambda mm: "[%s] " % mm.group(1).lower(), text)
        items.append({"type": "listItem", "content": [paragraph(text)]})
        i += 1

    return {"type": "bulletList" if not ordered else "orderedList", "content": items}, i


def extract_section(lines, heading):
    """Return the lines of one `## Heading` section, heading line included."""
    target = heading.strip()
    level = len(target) - len(target.lstrip("#"))
    out = []
    inside = False
    for line in lines:
        h = HEADING_RE.match(line)
        if h:
            this_level = len(h.group(1))
            if line.strip() == target:
                inside = True
                out.append(line)
                continue
            if inside and this_level <= level:
                break
        if inside:
            out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser(description="Markdown → Atlassian Document Format (ADF)")
    ap.add_argument("input", help="markdown file, or - for stdin")
    ap.add_argument("-o", "--output", help="write ADF JSON here (default: stdout)")
    ap.add_argument("--section", help='extract only this heading, e.g. "## QA 가이드"')
    ap.add_argument("--drop-heading", action="store_true",
                    help="omit the section's own heading line from the output")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    lines = raw.replace("\r\n", "\n").split("\n")

    if args.section:
        lines = extract_section(lines, args.section)
        if not lines:
            sys.exit("section not found: %s" % args.section)
        if args.drop_heading:
            lines = lines[1:]

    doc = {"version": 1, "type": "doc", "content": convert(lines)}
    if not doc["content"]:
        sys.exit("nothing to convert (empty document)")

    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
        counts = {}
        def tally(node):
            counts[node["type"]] = counts.get(node["type"], 0) + 1
            for child in node.get("content", []):
                tally(child)
        for node in doc["content"]:
            tally(node)
        summary = ", ".join("%s=%d" % kv for kv in sorted(counts.items()))
        print("wrote %s (%s)" % (args.output, summary))
    else:
        print(payload)


if __name__ == "__main__":
    main()
