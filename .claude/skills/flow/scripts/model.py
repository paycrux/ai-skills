"""Shared document model for flow.py, render.py, browser.py and migrate.py."""
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CORE_STAGES = [
    ("plan", "기획"),
    ("screen", "화면 · SOT 맵"),
    ("grill", "질문"),
    ("tasks", "구현 계획 · 구현"),
    ("verify", "검증"),
    ("done", "완료"),
    ("release", "배포"),
]
CORE_PAGES = [
    ("plan", "기획 · 화면", "01-plan.html", ("plan", "screen")),
    ("grill", "질문", "02-grill.html", ("grill",)),
    ("tasks", "구현 계획 · 구현", "03-tasks.html", ("tasks",)),
    ("verify", "검증", "04-verify.html", ("verify",)),
    ("done", "완료", "05-done.html", ("done",)),
    ("release", "배포", "06-release.html", ("release",)),
]
CORE_KEYS = [k for k, _ in CORE_STAGES]
# The live catalog: the core stages plus the active plugins' own stages, with labels applied.
# workflow.use(docs) refreshes these in place, so every module that imported them sees the change.
STAGES = list(CORE_STAGES)
PAGES = list(CORE_PAGES)
STAGE_KEYS = list(CORE_KEYS)
STAGE_TITLE = dict(CORE_STAGES)
STAGE_FILE = {k: f for _, _, f, keys in CORE_PAGES for k in keys}
PAGE_OF = {k: page for page, _, _, keys in CORE_PAGES for k in keys}
# Stages the person is involved in: shown in their pages, and Claude stops for them there. A stage
# outside this set is still created, filled and checked like any other — turning it off never stops data.
ENABLED = set(CORE_KEYS)
CUSTOM = {}


def apply_workflow(custom=(), labels=None, enabled=None):
    """Rebuild the live catalog. custom: [{"key", "title", "after"}] in plugin order."""
    labels = labels or {}
    stages, pages = list(CORE_STAGES), list(CORE_PAGES)
    for c in custom:
        at = next((i for i, (k, _) in enumerate(stages) if k == c["after"]), len(stages) - 1)
        while at + 1 < len(stages) and ":" in stages[at + 1][0]:
            at += 1
        stages.insert(at + 1, (c["key"], c["title"]))
        pat = next((i for i, (_, _, _, keys) in enumerate(pages) if stages[at][0] in keys), len(pages) - 1)
        pages.insert(pat + 1, (c["key"], c["title"], foreign_file(c["key"]), (c["key"],)))
    titles = {k: labels.get(k, t) for k, t in stages}
    STAGES[:] = [(k, titles[k]) for k, _ in stages]
    PAGES[:] = [(page, " · ".join(titles[k] for k in keys) if any(k in labels for k in keys) else title, f, keys)
                for page, title, f, keys in pages]
    STAGE_KEYS[:] = [k for k, _ in stages]
    STAGE_TITLE.clear()
    STAGE_TITLE.update(titles)
    STAGE_FILE.clear()
    STAGE_FILE.update({k: f for _, _, f, keys in PAGES for k in keys})
    PAGE_OF.clear()
    PAGE_OF.update({k: page for page, _, _, keys in PAGES for k in keys})
    ENABLED.clear()
    ENABLED.update(STAGE_KEYS if enabled is None else enabled)
    CUSTOM.clear()
    CUSTOM.update({c["key"]: c for c in custom})


def foreign_file(key):
    return f"x-{key.replace(':', '-')}.html"


def is_plugin_key(key):
    return bool(re.fullmatch(r"[a-z][a-z0-9-]*:[a-z][a-z0-9-]*", str(key)))


def task_keys(task):
    """The task's stage keys in catalog order; a plugin stage whose plugin is not active here goes last."""
    stages = task.get("stages") or {}
    return [k for k in STAGE_KEYS if k in stages] + [k for k in stages if k not in STAGE_KEYS and is_plugin_key(k)]


def task_pages(task):
    """PAGES plus a plain page for each plugin stage of this task whose plugin is not active here."""
    extra = [(k, k, foreign_file(k), (k,)) for k in task_keys(task) if k not in STAGE_KEYS]
    return PAGES + extra


def page_file(key):
    return STAGE_FILE.get(key) or foreign_file(key)


STATUSES = ("done", "now", "ask", "wait")
STATE_LABEL = {"done": "완료", "now": "진행 중", "ask": "질문 · 결정 대기", "wait": "시작 전", "skip": "건너뜀"}
KINDS = {"screens": ("server", "format", "calc", "action", "pending", "out"),
         "components": ("prop", "slot", "state", "token", "pending", "out")}
KIND = {
    "server": ("Data", "data"), "format": ("Computed", "comp"), "calc": ("Computed · 계산", "comp"),
    "action": ("Action", "act"), "pending": ("확인 필요", "pend"), "out": ("범위 제외", "out"),
    "prop": ("Prop", "data"), "slot": ("Slot", "comp"), "state": ("State", "act"), "token": ("Token", "comp"),
}
ITEM_ID = re.compile(r"^(S\d+|X\d+|R\d+(-Q\d+)?|P\d+(-[A-Za-z0-9]+)?|C\d+(-\d+)?|[BVDLE]\d+)$")
REF = re.compile(r"\[\[([^\]\s]+)\]\]")
RESERVED_TASK_IDS = {"tasks", "images", "diagrams", "verify", "index"}
DEFAULT_OPTIONS = [{"value": "yes", "label": "추천대로"}, {"value": "no", "label": "다르게"}]
UNSURE = {"value": "unsure", "label": "더 설명해줘"}
REASON_BY = {"user": "본인 말", "recommended": "추천대로 고름 · 추천 이유", "plan": "기획 · 디자인", "backend": "백엔드",
             "inferred": "추정 · 확인 전"}


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


def stage_skeleton(key):
    if key == "plan":
        return {"status": "now", "summary": "작성 중", "conclusion": [],
                "blocks": [{"type": "quote", "title": "기획서 발췌", "items": []}, {"type": "text", "title": "디자인", "html": ""}]}
    if key == "screen":
        return {"status": "wait", "summary": "시작 전", "conclusion": []}
    if key == "grill":
        return {"rounds": []}
    if key == "tasks":
        return {"status": "wait", "summary": "계획 작성 전", "conclusion": [], "blocks": []}
    if key == "verify":
        return {"status": "wait", "summary": "검증 전", "conclusion": [],
                "blocks": [{"type": "checklist", "title": "화면 밖 상태 확인", "items": []},
                           {"type": "checklist", "title": "버그", "items": []}]}
    if key == "release":
        return {"status": "wait", "summary": "배포 전", "conclusion": [],
                "blocks": [{"type": "checklist", "title": "배포", "items": [
                    {"id": "L1", "title": "배포 환경(dev · stg)에 반영됨", "done": False},
                    {"id": "L2", "title": "배포된 화면에서 주요 상태를 확인함", "done": False},
                    {"id": "L3", "title": "Jira 이슈를 완료 상태로 옮김 — 사람이 옮길 것이면 결론에 기록", "done": False}]}]}
    if key != "done":
        return {"status": "wait", "summary": "시작 전", "conclusion": [], "blocks": []}
    return {"status": "wait", "summary": "리뷰 전", "conclusion": [],
            "blocks": [{"type": "checklist", "title": "PR 전", "items": [
                {"id": "D1", "title": "SOT 맵 근거를 실제 코드 파일:줄로 바꿈", "done": False},
                {"id": "D2", "title": "남은 Computed · 계산 행을 서버 · 기획 요청으로 정리", "done": False},
                {"id": "D3", "title": "<code>/code-review</code> — 크리티컬한 지적을 고침", "done": False},
                {"id": "D4", "title": "고친 뒤 typecheck · lint · test 다시 통과 (04 검증이 있으면 그것도 완료)", "done": False},
                {"id": "D5", "title": "PR — <code>/git-pr</code>로 만들거나, 안 만들면 결론에 기록", "done": False}]},
                {"type": "text", "title": "서버 · 기획에 요청할 것", "html": "없어요"}]}


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
    """(items, resolved). An item nobody can collect (`unknown`) counts as resolved: it is reported,
    never invented, and it does not hold the stage or the task open."""
    total = done = 0
    for b in (stage or {}).get("blocks", []):
        if b.get("type") != "checklist":
            continue
        for it in b.get("items", []):
            total += 1
            done += 1 if it.get("done") or it.get("unknown") else 0
    return total, done


def unconfirmed(task):
    """What went in without a person: inferred decisions and items, stops skipped, values nobody could collect."""
    out = {"inferred": [], "skipped": list(task.get("skipped") or []), "unknown": []}
    for key in task_keys(task):
        st = task["stages"][key]
        if key == "grill":
            for r in st.get("rounds", []):
                for q in r.get("questions", []):
                    if (q.get("reason") or {}).get("by") == "inferred":
                        out["inferred"].append(f"{r['id']}-{q['id']}")
            continue
        for pid, ext in (st.get("ext") or {}).items():
            # unknown / inferred are the two names flow reads inside a plugin's ext (see plugin.md).
            if isinstance(ext, dict):
                out["inferred"] += [f"{key} · {pid}.{f}" for f in ext.get("inferred") or [] if isinstance(f, str)]
                if isinstance(ext.get("unknown"), dict):
                    out["unknown"] += [(f"{key} · {pid}.{f}", str(why)) for f, why in ext["unknown"].items()]
        for b in st.get("blocks", []):
            for it in b.get("items", []) if b.get("type") == "checklist" else []:
                if it.get("by") == "inferred":
                    out["inferred"].append(it.get("id", ""))
                if it.get("unknown"):
                    out["unknown"].append((it.get("id", ""), str(it["unknown"])))
    return out


def unconfirmed_line(task):
    u = unconfirmed(task)
    parts = [f"{label} {len(u[k])}건" for k, label in
             (("inferred", "사람 확인 안 된 추정"), ("skipped", "건너뛴 멈춤"), ("unknown", "모르는 값")) if u[k]]
    return " · ".join(parts)


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


def page_state(task, keys):
    live = [s for s in (stage_state(task, k) for k in keys) if s["status"] != "skip"]
    if not live:
        return {"status": "skip", "summary": "필요하면 생겨요"}
    statuses = [s["status"] for s in live]
    if "ask" in statuses or "now" in statuses:
        status = "ask" if "ask" in statuses else "now"
    elif all(x == "done" for x in statuses):
        status = "done"
    else:
        status = "now" if "done" in statuses else "wait"
    return {"status": status, "summary": " · ".join(s["summary"] for s in live if s["summary"])}


def task_state(task):
    """A task is done only when it is finished (see finished) — every stage done is not enough."""
    s = stages_state(task)
    if s == "done" and not (task.get("pruned") or finished(task)):
        return "now"
    return s


def finished(task):
    """Over and ready to prune: every stage done, and a 05 완료 stage whose checklist — review,
    the critical fixes, tests run again after them, the PR — is all ticked. Implementation alone is not.
    A workflow that turns 05 완료 off changes none of this: off only means the person is not stopped there."""
    st = (task.get("stages") or {}).get("done")
    if not st or stages_state(task) != "done":
        return False
    total, ticked = checklist_count(st)
    return bool(total) and ticked == total


def stages_state(task):
    states = [stage_state(task, k) for k in task_keys(task)]
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
            if k not in ("id", "ext"):
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
            for k, v in node.items():
                if k != "ext":
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
