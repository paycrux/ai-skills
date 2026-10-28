"""Read answers the pages left in a browser's localStorage, or in the clipboard.

The pages save each task's answers under the localStorage key
"flow:<absolute path of the task's page folder>/". Chromium browsers keep localStorage in a LevelDB
folder per profile; this module reads those files directly (no browser API, standard library only)
and only keys that start with "flow:".
"""
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

from model import DEFAULT_OPTIONS, UNSURE

HOME = Path.home()
MAC = HOME / "Library/Application Support"
BROWSER_ROOTS = [
    MAC / "Google/Chrome", MAC / "Google/Chrome Beta", MAC / "Google/Chrome Canary", MAC / "Chromium",
    MAC / "Aside", MAC / "Arc/User Data", MAC / "Dia/User Data", MAC / "Microsoft Edge", MAC / "BraveSoftware/Brave-Browser",
    MAC / "Vivaldi", MAC / "com.openai.atlas/browser-data/host", MAC / "Comet", MAC / "com.operasoftware.Opera",
    HOME / ".config/google-chrome", HOME / ".config/chromium", HOME / ".config/microsoft-edge",
    HOME / ".config/BraveSoftware/Brave-Browser", HOME / ".config/vivaldi",
]
BROWSER_ROOTS += [Path(p) for p in os.environ.get("FLOW_BROWSER_DIRS", "").split(os.pathsep) if p]
if os.environ.get("LOCALAPPDATA"):
    _local = Path(os.environ["LOCALAPPDATA"])
    BROWSER_ROOTS += [_local / "Google/Chrome/User Data", _local / "Microsoft/Edge/User Data",
                      _local / "BraveSoftware/Brave-Browser/User Data", _local / "Chromium/User Data"]
ORIGIN = b"_file://\x00"
ORIGIN_END = b"_file://\x01"


# ---------------------------------------------------------------- LevelDB

def varint(b, i):
    r = s = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        if c < 0x80:
            return r, i
        s += 7


def snappy(b):
    n, i = varint(b, 0)
    out = bytearray()
    while i < len(b):
        t = b[i]
        i += 1
        k = t & 3
        if k == 0:
            ln = t >> 2
            if ln >= 60:
                nb = ln - 59
                ln = int.from_bytes(b[i:i + nb], "little")
                i += nb
            ln += 1
            out += b[i:i + ln]
            i += ln
            continue
        if k == 1:
            ln = ((t >> 2) & 7) + 4
            off = ((t >> 5) << 8) | b[i]
            i += 1
        elif k == 2:
            ln = (t >> 2) + 1
            off = int.from_bytes(b[i:i + 2], "little")
            i += 2
        else:
            ln = (t >> 2) + 1
            off = int.from_bytes(b[i:i + 4], "little")
            i += 4
        start = len(out) - off
        for j in range(ln):
            out.append(out[start + j])
    return bytes(out[:n])


def block_entries(raw):
    nr = struct.unpack("<I", raw[-4:])[0]
    end = len(raw) - 4 - 4 * nr
    i, key = 0, b""
    while i < end:
        shared, i = varint(raw, i)
        nonshared, i = varint(raw, i)
        vlen, i = varint(raw, i)
        key = key[:shared] + raw[i:i + nonshared]
        i += nonshared
        yield key, raw[i:i + vlen]
        i += vlen


def read_block(data, off, size):
    raw = data[off:off + size]
    return snappy(raw) if data[off + size] == 1 else raw


def table_records(path):
    data = path.read_bytes()
    foot = data[-48:]
    _, i = varint(foot, 0)
    _, i = varint(foot, i)
    idx_off, i = varint(foot, i)
    idx_size, _ = varint(foot, i)
    prev = b""
    for sep, handle in block_entries(read_block(data, idx_off, idx_size)):
        if prev < ORIGIN_END and sep >= ORIGIN:
            off, j = varint(handle, 0)
            size, _ = varint(handle, j)
            for ikey, val in block_entries(read_block(data, off, size)):
                if ikey.startswith(ORIGIN):
                    tag = struct.unpack("<Q", ikey[-8:])[0]
                    yield ikey[:-8], val, tag >> 8, tag & 0xFF
        prev = sep


def log_records(path):
    data = path.read_bytes()
    pos, buf, batches = 0, b"", []
    while pos + 7 <= len(data):
        left = 32768 - pos % 32768
        if left < 7:
            pos += left
            continue
        ln, typ = struct.unpack("<HB", data[pos + 4:pos + 7])
        frag = data[pos + 7:pos + 7 + ln]
        pos += 7 + ln
        if (typ == 0 and ln == 0) or len(frag) < ln:
            break
        buf = frag if typ in (1, 2) else buf + frag
        if typ in (1, 4):
            batches.append(buf)
    for b in batches:
        if len(b) < 12:
            continue
        seq, count = struct.unpack("<QI", b[:12])
        i = 12
        try:
            for n in range(count):
                kind = b[i]
                i += 1
                kl, i = varint(b, i)
                key = b[i:i + kl]
                i += kl
                val = None
                if kind == 1:
                    vl, i = varint(b, i)
                    val = b[i:i + vl]
                    i += vl
                if key.startswith(ORIGIN):
                    yield key, val, seq + n, kind
        except IndexError:
            continue


def decode(b):
    if not b:
        return ""
    return b[1:].decode("utf-16-le", "replace") if b[0] == 0 else b[1:].decode("latin-1")


def file_storage(folder, prefixes):
    """{localStorage key: value} for file:// pages in one LevelDB folder, keys starting with a prefix."""
    latest = {}
    for p in sorted(folder.iterdir()):
        if p.suffix not in (".ldb", ".log"):
            continue
        try:
            recs = list(table_records(p) if p.suffix == ".ldb" else log_records(p))
        except (OSError, IndexError, struct.error, ValueError):
            continue
        for key, val, seq, kind in recs:
            k = decode(key[len(ORIGIN):])
            if not k.startswith(prefixes):
                continue
            if k not in latest or seq > latest[k][0]:
                latest[k] = (seq, kind, val)
    return {k: decode(v) for k, (_, kind, v) in latest.items() if kind == 1}


def storage_folders():
    out = []
    for root in BROWSER_ROOTS:
        if not root.is_dir():
            continue
        for dirpath, dirnames, _ in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            if Path(dirpath).name == "leveldb" and Path(dirpath).parent.name == "Local Storage":
                out.append(Path(dirpath))
                dirnames[:] = []
            elif depth >= 3 or Path(dirpath).name in ("Extensions", "Storage", "Cache", "Code Cache", "Service Worker"):
                dirnames[:] = []
    return out


def browser_label(folder):
    for root in BROWSER_ROOTS:
        try:
            rel = folder.relative_to(root)
        except ValueError:
            continue
        name = root.name if root.name not in ("User Data", "host") else root.parent.name
        return f"{name} · {rel.parts[0]}" if rel.parts else name
    return str(folder)


def task_of(key, docs):
    """'flow:<page folder>/' → '<domain>/<task>' when the folder is a task folder under docs."""
    path = key[len("flow:"):]
    if re.fullmatch(r"/[A-Za-z]:/.*", path):
        path = path[1:]
    try:
        rel = Path(path).resolve().relative_to(Path(docs).resolve())
    except (ValueError, OSError):
        return None
    return "/".join(rel.parts) if len(rel.parts) == 2 else None


def browser_answers(docs):
    """→ {"<domain>/<task>": (state dict, browser label)} — the newest copy of each task's answers."""
    found = {}
    for folder in storage_folders():
        for key, value in file_storage(folder, ("flow:",)).items():
            tag = task_of(key, docs)
            if not tag:
                continue
            try:
                state = json.loads(value)
            except ValueError:
                continue
            if tag not in found or state.get("updatedAt", 0) > found[tag][0].get("updatedAt", 0):
                found[tag] = (state, browser_label(folder))
    return found


# ---------------------------------------------------------------- clipboard

HEADER = re.compile(r"^\[flow 답 · ([^/\s]+)/(\S+) · .*?t=(\d+)\]\s*$")
QUESTION = re.compile(r"^(R\d+-Q\d+) ")
FIELD = re.compile(r"^  (답|문구|메모|되물음): ?(.*)$")
CHECK = re.compile(r"^  \[(x| )\] (\S+)")
FIELD_KEY = {"답": "label", "문구": "copy", "메모": "note", "되물음": "followUp"}


def read_clipboard():
    cmds = [["pbpaste"], ["wl-paste", "--no-newline"], ["xclip", "-o", "-selection", "clipboard"],
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"]]
    for cmd in cmds:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    sys.exit("클립보드를 읽을 명령이 없어요 (pbpaste · wl-paste · xclip · powershell)")


def parse_copied(text):
    """The page's '답 복사' text → (domain, task, state) or None when it is not a flow answer."""
    lines = text.replace("\r\n", "\n").split("\n")
    head = next((HEADER.match(l) for l in lines if l.strip()), None)
    if not head:
        return None
    domain, task, stamp = head.group(1), head.group(2), int(head.group(3))
    answers, checks = {}, {}
    cur, field, in_checks = None, None, False
    for line in lines[1:]:
        if line == "체크":
            in_checks, cur, field = True, None, None
            continue
        m = QUESTION.match(line)
        if m and not in_checks:
            cur, field = answers.setdefault(m.group(1), {}), None
            continue
        m = FIELD.match(line)
        if m and cur is not None:
            field = FIELD_KEY[m.group(1)]
            cur[field] = m.group(2)
            continue
        if line.startswith("    ") and cur is not None and field:
            cur[field] += "\n" + line[4:]
            continue
        m = CHECK.match(line)
        if m and in_checks:
            checks[m.group(2)] = m.group(1) == "x"
    return domain, task, {"updatedAt": stamp, "labels": answers, "checks": checks}


# ---------------------------------------------------------------- write into the task JSON

def label_to_value(q, label):
    if not label or label == "답 없음":
        return ""
    for o in (q.get("options") or DEFAULT_OPTIONS) + [UNSURE]:
        if o.get("label") == label:
            return o["value"]
    return label


def merge(task, state):
    """Write a page state into the task as "by": "user" marks. → lines describing what changed."""
    changed = []
    rounds = {r["id"]: r for r in ((task.get("stages") or {}).get("grill") or {}).get("rounds", [])}
    labels = state.get("labels")
    answers = state.get("answers") or {}
    for tag in list(answers) + list(labels or {}):
        rid, _, qid = tag.partition("-")
        q = next((x for x in rounds.get(rid, {}).get("questions", []) if x.get("id") == qid), None)
        if q is None:
            changed.append(f"{tag}: 작업에 없는 질문이라 건너뜀")
            continue
        if labels is not None and tag in labels:
            src = labels[tag]
            new = {"choice": label_to_value(q, src.get("label", "")), "note": src.get("note", ""), "followUp": src.get("followUp", ""), "copy": src.get("copy", "")}
        else:
            src = answers[tag]
            new = {k: src.get(k, "") for k in ("choice", "note", "followUp", "copy")}
        cur = q.get("answer") or {}
        if all((cur.get(k) or "") == new[k] for k in new):
            continue
        q["answer"] = {**new, "by": "user"}
        changed.append(f"{tag}: 답 '{new['choice'] or '없음'}'" + (f" · 문구 \"{new['copy']}\"" if new["copy"] else "") + (f" · 메모 \"{new['note']}\"" if new["note"] else "")
                       + (f" · 되물음 \"{new['followUp']}\"" if new["followUp"] else ""))
    items = {}
    for key, st in (task.get("stages") or {}).items():
        for b in st.get("blocks", []) if key != "grill" else []:
            for it in b.get("items", []) if b.get("type") == "checklist" else []:
                items[it["id"]] = it
    for cid, done in (state.get("checks") or {}).items():
        it = items.get(cid)
        if it is None:
            changed.append(f"{cid}: 작업에 없는 체크 항목이라 건너뜀")
            continue
        if bool(it.get("done")) == bool(done):
            continue
        it["done"] = bool(done)
        it["by"] = "user"
        changed.append(f"{cid}: {'체크' if done else '체크 해제'}")
    stamp = int(state.get("updatedAt") or 0)
    if stamp > int(task.get("pulledAt") or 0):
        task["pulledAt"] = stamp
    return changed
