"""Shared document model for flow.py, render.py, browser.py and migrate.py."""
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

STAGES = [
    ("plan", "기획", "01-plan.html"),
    ("screen", "화면 · SOT 맵", "02-screen.html"),
    ("grill", "질문", "03-grill.html"),
    ("tasks", "구현 계획 · 구현", "04-tasks.html"),
    ("verify", "검증", "05-verify.html"),
    ("done", "완료", "06-done.html"),
]
STAGE_KEYS = [k for k, _, _ in STAGES]
STAGE_TITLE = {k: t for k, t, _ in STAGES}
STAGE_FILE = {k: f for k, _, f in STAGES}
STATUSES = ("done", "now", "ask", "wait")
STATE_LABEL = {"done": "완료", "now": "진행 중", "ask": "질문 · 결정 대기", "wait": "시작 전", "skip": "건너뜀"}
KINDS = {"screens": ("server", "format", "calc", "action", "pending", "out"),
         "components": ("prop", "slot", "state", "token", "pending", "out")}
KIND = {
    "server": ("Data", "data"), "format": ("Computed", "comp"), "calc": ("Computed · 계산", "comp"),
    "action": ("Action", "act"), "pending": ("확인 필요", "pend"), "out": ("범위 제외", "out"),
    "prop": ("Prop", "data"), "slot": ("Slot", "comp"), "state": ("State", "act"), "token": ("Token", "comp"),
}
ITEM_ID = re.compile(r"^(S\d+|X\d+|R\d+(-Q\d+)?|P\d+(-[A-Za-z0-9]+)?|C\d+(-\d+)?|[BVD]\d+)$")
REF = re.compile(r"\[\[([^\]\s]+)\]\]")
RESERVED_TASK_IDS = {"tasks", "images", "index"}
DEFAULT_OPTIONS = [{"value": "yes", "label": "추천대로"}, {"value": "no", "label": "다르게"}]
UNSURE = {"value": "unsure", "label": "더 설명해줘"}


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        if default is not None:
            return default
        sys.exit(f"없는 파일: {path}")
    return json.loads(path.read_text())


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def git(cwd, *args):
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError):
        return ""


def plain(text):
    return re.sub(r"<[^>]+>", "", str(text))


def domains_of(docs):
    return sorted(p for p in Path(docs).iterdir() if p.is_dir() and (p / "domain.json").exists())


def scope(target):
    """A docs folder or one domain folder → (docs root, [domain dirs])."""
    t = Path(target)
    if (t / "domain.json").exists():
        return t.parent, [t]
    if not t.is_dir():
        sys.exit(f"없는 폴더: {t}")
    return t, domains_of(t)


def task_files(domain_dir):
    return sorted((Path(domain_dir) / "tasks").glob("*.json"))


# ---------------------------------------------------------------- stage state

def grill_state(stage):
    rounds = (stage or {}).get("rounds", [])
    decided, open_, revised = 0, [], []
    for r in rounds:
        qs = r.get("questions", [])
        is_open = any(not q.get("decision") for q in qs)
        is_revised = not is_open and any((q.get("answer") or {}).get("by") == "user" for q in qs)
        if is_open:
            open_.append(r["id"])
        elif is_revised:
            revised.append(r["id"])
        else:
            decided += len(qs)
    if not rounds:
        status, summary = "wait", "질문 없음"
    elif open_ or revised:
        status = "ask"
        summary = " · ".join([f"{i} 답 대기" for i in open_] + [f"{i} 답 수정됨" for i in revised])
    else:
        status, summary = "done", f"남은 질문 0 · 결정 {decided}"
    return {"status": status, "summary": summary, "open": open_, "revised": revised, "decided": decided}


def checklist_count(stage):
    total = done = 0
    for b in (stage or {}).get("blocks", []):
        if b.get("type") != "checklist":
            continue
        for it in b.get("items", []):
            total += 1
            done += 1 if it.get("done") else 0
    return total, done


def stage_state(task, key):
    stage = (task.get("stages") or {}).get(key)
    if stage is None:
        return {"status": "skip", "summary": "필요하면 생겨요"}
    if key == "grill":
        return grill_state(stage)
    status = stage.get("status") if stage.get("status") in STATUSES else "wait"
    summary = stage.get("summary", "")
    total, done = checklist_count(stage)
    if total:
        summary = f"{summary}{' · ' if summary else ''}체크 {done}/{total}"
    return {"status": status, "summary": summary}


def task_state(task):
    states = [stage_state(task, k) for k in STAGE_KEYS]
    states = [s for s in states if s["status"] != "skip"]
    if not states:
        return "wait"
    if any(s["status"] == "ask" for s in states):
        return "ask"
    if any(s["status"] == "now" for s in states):
        return "now"
    if all(s["status"] == "done" for s in states):
        return "done"
    if any(s["status"] == "done" for s in states):
        return "now"
    return "wait"


# ---------------------------------------------------------------- references

def walk_refs(node, owner, visit):
    if isinstance(node, str):
        for m in REF.finditer(node):
            visit(m.group(1), owner)
    elif isinstance(node, list):
        for x in node:
            walk_refs(x, owner, visit)
    elif isinstance(node, dict):
        here = owner
        if isinstance(node.get("id"), str) and ITEM_ID.match(node["id"]):
            here = node["id"]
        elif isinstance(node.get("id"), str) and re.fullmatch(r"Q\d+", node["id"]) and re.fullmatch(r"R\d+", owner or ""):
            here = f"{owner}-{node['id']}"
        for k, v in node.items():
            if k != "id":
                walk_refs(v, here, visit)


def parse_ref(raw, domain, task):
    """[[raw]] seen inside (domain, task) → (domain, task or None, item or None)."""
    item = raw
    if "/" in raw:
        domain, item = raw.split("/", 1)
    if "#" in item:
        t, item = item.split("#", 1)
        return domain, t, item
    if not ITEM_ID.match(item):
        return domain, item, None
    if re.fullmatch(r"[SX]\d+", item):
        return domain, None, item
    return domain, task, item


def task_items(task):
    """Every addressable ID in a task → (stage key, node)."""
    out = {}

    def visit(node, key):
        if isinstance(node, dict):
            if isinstance(node.get("id"), str) and ITEM_ID.match(node["id"]):
                out.setdefault(node["id"], (key, node))
            for v in node.values():
                visit(v, key)
        elif isinstance(node, list):
            for v in node:
                visit(v, key)

    for key, st in (task.get("stages") or {}).items():
        if key == "grill":
            for r in st.get("rounds", []):
                out[r["id"]] = ("grill", r)
                for q in r.get("questions", []):
                    out[f"{r['id']}-{q['id']}"] = ("grill", q)
            visit(st.get("blocks", []), key)
            continue
        visit(st, key)
    return out


# ---------------------------------------------------------------- Figma structure

def frame_boxes(path):
    root = ET.fromstring(Path(path).read_text())
    boxes = {}

    def walk(node, ox, oy, top):
        x = ox + (0 if top else float(node.get("x", 0)))
        y = oy + (0 if top else float(node.get("y", 0)))
        boxes[node.get("id")] = (x, y, float(node.get("width", 0)), float(node.get("height", 0)))
        for child in node:
            walk(child, x, y, False)

    walk(root, 0, 0, True)
    return float(root.get("width", 0)), float(root.get("height", 0)), boxes


def place(marker, width, boxes):
    if not marker.get("node"):
        return marker.get("x"), marker.get("y")
    b = boxes.get(marker["node"])
    if b is None:
        return None
    x, y, w, h = b
    side = marker.get("side")
    if side == "top":
        return x + w / 2, max(12, y - 12)
    if side == "bottom":
        return x + w / 2, y + h + 12
    right = x + w + 14
    if side == "left" or right > width - 12:
        return max(12, x - 14), y + h / 2
    return right, y + h / 2
