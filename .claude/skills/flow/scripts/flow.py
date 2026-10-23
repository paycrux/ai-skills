"""Set up and check /flow documents.

    python3 flow.py install <docs>                          copy the server + viewer to <docs>/.flow, add "flow" to package.json
    python3 flow.py find <docs> [--node ID] [--name TEXT] [--path PATH]
    python3 flow.py domain <docs> <domain-id> --title "..." [--kind screens|components] [--figma "..."] [--node ID]... [--path PATH]...
    python3 flow.py task <docs>/<domain> <task-id> --title "..." [--type "..."] [--stages plan,screen,tasks]
    python3 flow.py add <docs>/<domain>/tasks/<task>.json <stage>...
    python3 flow.py brief <docs>/<domain>/tasks/<task>.json [--stage KEY]   what Claude reads to resume
    python3 flow.py changes <docs | docs/domain>          what the person changed in the viewer ("by": "user")
    python3 flow.py clear <file.json> [--id ID]...          drop "by": "user" once handled
    python3 flow.py check <docs | docs/domain>
    python3 flow.py merge-xml <base.xml> <expanded.xml>... -o <out.xml>

Layout:

    <docs>/.flow/            server.mjs + viewer/ (copied by install; never edit there)
    <docs>/<domain>/
      domain.json            title, figma, nodes, paths, links
      screens.json           SOT map of the domain's screens (markers S1…, off-screen states X1…)
      tasks/<task-id>.json   one per task: stages plan · screen · grill · tasks · verify · done
      images/                Figma screenshots and structure XML

Everything else under <docs> is legacy: listed by the viewer, never written.
Standard library only, Python 3.9+.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
RUNTIME = SKILL / "runtime"
STAGES = ["plan", "screen", "grill", "tasks", "verify", "done"]
STATUSES = ("done", "now", "ask", "wait")
KINDS = {"screens": ("server", "format", "calc", "action", "pending", "out"),
         "components": ("prop", "slot", "state", "token", "pending", "out")}
ITEM_ID = re.compile(r"^(S\d+|X\d+|R\d+(-Q\d+)?|P\d+(-[A-Za-z0-9]+)?|[BVD]\d+)$")
REF = re.compile(r"\[\[([^\]\s]+)\]\]")
SCRIPT = "node docs/.flow/server.mjs"


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
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


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
    return {"status": "wait", "summary": "PR 전", "conclusion": [],
            "blocks": [{"type": "checklist", "title": "PR 전", "items": [
                {"id": "D1", "title": "SOT 맵 근거를 실제 코드 파일:줄로 바꿈", "done": False},
                {"id": "D2", "title": "남은 Computed · 계산 행을 서버 · 기획 요청으로 정리", "done": False},
                {"id": "D3", "title": "PR 생성", "done": False}]},
                {"type": "text", "title": "서버 · 기획에 요청할 것", "html": "없어요"}]}


def parse_stages(text):
    keys = [k.strip() for k in text.split(",") if k.strip()]
    bad = [k for k in keys if k not in STAGES]
    if bad:
        sys.exit(f"없는 단계: {', '.join(bad)} — {' · '.join(STAGES)} 중에서")
    return keys


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


# ---------------------------------------------------------------- install / domain / task

def cmd_install(args):
    docs = Path(args.docs).resolve()
    docs.mkdir(parents=True, exist_ok=True)
    dest = docs / ".flow"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(RUNTIME, dest, ignore=shutil.ignore_patterns(".DS_Store"))
    print(f"서버 · 뷰어를 복사했어요: {dest}")
    top = Path(git(docs, "rev-parse", "--show-toplevel") or docs.parent)
    rel = docs.relative_to(top) if docs.is_relative_to(top) else None
    script = f"node {rel.as_posix()}/.flow/server.mjs" if rel else f"node {dest}/server.mjs"
    pkg = top / "package.json"
    if not pkg.exists():
        print(f"package.json이 없어요. 실행은: {script}")
        return
    data = json.loads(pkg.read_text())
    scripts = data.setdefault("scripts", {})
    if scripts.get("flow") == script:
        print("package.json에 flow 스크립트가 이미 있어요")
    elif "flow" in scripts:
        print(f"package.json의 flow 스크립트가 다른 명령이라 그대로 뒀어요: {scripts['flow']} — 실행은: {script}")
    else:
        scripts["flow"] = script
        indent = 2 if '\n  "' in pkg.read_text() else 4
        pkg.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n")
        print(f'package.json에 "flow": "{script}"를 넣었어요 — 공유 저장소 변경이니 팀에 한 번 알려 주세요')


def cmd_find(args):
    _, doms = scope(args.docs)
    hits = []
    for d in doms:
        info = read_json(d / "domain.json")
        why = []
        if args.node and args.node in (info.get("nodes") or []):
            why.append(f"Figma 노드 {args.node}")
        if args.node and args.node in json.dumps(read_json(d / "screens.json", {}), ensure_ascii=False):
            why.append(f"SOT 맵에 노드 {args.node}")
        if args.name and (args.name in info.get("title", "") or args.name in d.name):
            why.append(f"이름 '{args.name}'")
        if args.path and any(args.path.startswith(p) or p.startswith(args.path) for p in info.get("paths") or []):
            why.append(f"경로 {args.path}")
        if why:
            hits.append((d.name, info.get("title", ""), why))
    if not hits:
        print("맞는 도메인이 없어요 — 새 도메인이면 flow.py domain으로 만들어요")
        return
    for name, title, why in hits:
        print(f"{name} ({title}): {' · '.join(dict.fromkeys(why))}")


def cmd_domain(args):
    docs = Path(args.docs)
    root = docs / args.id
    if (root / "domain.json").exists():
        sys.exit(f"이미 있는 도메인이에요: {root} — 작업은 flow.py task로 추가해요")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.id):
        sys.exit("도메인 ID는 영어 소문자 · 숫자 · 하이픈으로 (예: gift, account-settings)")
    (root / "tasks").mkdir(parents=True, exist_ok=True)
    (root / "images").mkdir(exist_ok=True)
    write_json(root / "domain.json", {"title": args.title, "kind": args.kind, "figma": args.figma or "",
                                      "nodes": args.node or [], "paths": args.path or [], "links": []})
    write_json(root / "screens.json", {"api": "", "base": "", "flows": [], "screens": []})
    print(f"도메인을 만들었어요: {root}")


def cmd_task(args):
    root = Path(args.domain)
    if not (root / "domain.json").exists():
        sys.exit(f"도메인 폴더가 아니에요: {root}")
    path = root / "tasks" / f"{args.id}.json"
    if path.exists():
        sys.exit(f"이미 있는 작업이에요: {path}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", args.id):
        sys.exit("작업 ID는 지라 키(COMP-452)나 짧은 영어 이름(bug-bottom-inset)으로")
    stages = {k: stage_skeleton(k) for k in parse_stages(args.stages)}
    task = {"id": args.id, "title": args.title, "type": args.type,
            "branch": args.branch or git(root, "branch", "--show-current"), "links": [], "stages": stages}
    (root / "tasks").mkdir(exist_ok=True)
    write_json(path, task)
    print(f"작업을 만들었어요: {path} — 단계 {', '.join(stages)}")


def cmd_add(args):
    task = read_json(args.task)
    made = []
    for k in parse_stages(",".join(args.stages)):
        if k not in task["stages"]:
            task["stages"][k] = stage_skeleton(k)
            made.append(k)
    task["stages"] = {k: task["stages"][k] for k in STAGES if k in task["stages"]}
    write_json(args.task, task)
    print(f"추가했어요: {', '.join(made) if made else '이미 다 있어요'}")


# ---------------------------------------------------------------- brief

def plain(text):
    return re.sub(r"<[^>]+>", "", str(text))


def stage_line(key, st):
    if key == "grill":
        rounds = st.get("rounds", [])
        open_ = [r["id"] for r in rounds if any(not q.get("decision") for q in r.get("questions", []))]
        if not rounds:
            return "grill: 질문 없음"
        return f"grill: {'열림 ' + ', '.join(open_) if open_ else '모두 결정됨'}"
    return f"{key}: {st.get('status')} · {st.get('summary', '')}"


def cmd_brief(args):
    t = read_json(args.task)
    stages = t.get("stages", {})
    print(f"{t['id']} {t['title']} · {t.get('type', '')} · {t.get('branch', '')}")
    for k in STAGES:
        if k in stages:
            print("  " + stage_line(k, stages[k]))
    keys = [args.stage] if args.stage else [k for k in STAGES if k in stages]
    for k in keys:
        st = stages.get(k)
        if not st:
            continue
        print(f"\n[{k}]")
        if k == "grill":
            for r in st.get("rounds", []):
                for q in r.get("questions", []):
                    a = q.get("answer") or {}
                    head = f"{r['id']}-{q['id']} {plain(q.get('title', ''))}"
                    if q.get("decision"):
                        print(f"- {head} → {plain(q['decision'])}")
                    else:
                        print(f"- {head} → 답 대기" + (f" (답 {a.get('choice')})" if a.get("choice") else ""))
            continue
        for c in st.get("conclusion", []):
            print(f"- {plain(c)}")
        if args.stage:
            for b in st.get("blocks", []):
                if b.get("type") == "checklist":
                    print(f"  {b.get('id', '')} {plain(b.get('title', ''))}")
                    for it in b.get("items", []):
                        print(f"    [{'x' if it.get('done') else ' '}] {it['id']} {plain(it.get('title', ''))}")
    marks = len(list(user_marks(t)))
    if marks:
        print(f"\n사람이 바꾼 것 {marks}건 — flow.py changes")


# ---------------------------------------------------------------- changes / clear

def user_marks(node, trail=()):
    if isinstance(node, dict):
        if isinstance(node.get("id"), str):
            trail = trail + (node["id"],)
        if node.get("by") == "user":
            yield trail, node
        for k, v in node.items():
            if isinstance(v, dict):
                yield from user_marks(v, trail + (k,))
            elif isinstance(v, list):
                for x in v:
                    yield from user_marks(x, trail)


def question_tag(trail):
    r = next((x for x in trail if re.fullmatch(r"R\d+", str(x))), None)
    q = next((x for x in trail if re.fullmatch(r"Q\d+", str(x))), None)
    return f"{r}-{q}" if r and q else None


def describe(trail, node):
    where = " ".join(str(t) for t in trail if t != "stages")
    if "choice" in node:
        tag = question_tag(trail) or where
        lines = []
        if node.get("choice") == "unsure":
            lines.append(f"{tag}: '더 설명해줘' — 빠진 설명을 붙여 다음 라운드에서 다시 물어요")
        else:
            note = f" · 메모 \"{node['note']}\"" if node.get("note") else ""
            lines.append(f"{tag}: 답 '{node.get('choice')}'{note} — 결정 문장을 쓰거나 고치고 반영한 곳(appliedTo)에 옮겨요")
        if node.get("followUp"):
            lines.append(f"{tag}: 되물음 \"{node['followUp']}\" — 답해야 해요")
        return lines
    if "done" in node:
        return [f"{node.get('id', where)}: 사람이 {'체크' if node['done'] else '체크 해제'}함 — {node.get('title', '')}"]
    if "conclusion" in node:
        return [f"{where}: 결론 문장을 사람이 고침 — 읽고 다음 단계에 반영해요"]
    return [f"{where}: '{node.get('title', '')}' 본문을 사람이 고침 — 읽고 반영해요"]


def cmd_changes(args):
    docs, doms = scope(args.target)
    found = 0
    for d in doms:
        for f in [d / "domain.json", d / "screens.json", *sorted((d / "tasks").glob("*.json"))]:
            if not f.exists():
                continue
            marks = list(user_marks(read_json(f)))
            if not marks:
                continue
            print(f"{f.relative_to(docs)}")
            for trail, node in marks:
                for line in describe(trail, node):
                    print(f"- {line}")
                    found += 1
    if not found:
        print("사람이 바꾼 것이 없어요")
    else:
        print("\n바뀐 내용 전체: git diff -- " + " ".join(str(d) for d in doms) + "\n처리한 뒤: flow.py clear <파일> [--id …]")


def cmd_clear(args):
    data = read_json(args.file)
    ids = set(args.id or [])
    marks = list(user_marks(data))
    for trail, node in marks:
        names = {node.get("id"), question_tag(trail) if "choice" in node else None, trail[-1] if trail else None}
        if not ids or names & ids:
            del node["by"]
    write_json(args.file, data)
    left = len(list(user_marks(data)))
    print(f"정리했어요: {args.file}" + (f" — 남은 표시 {left}" if left else ""))


# ---------------------------------------------------------------- check

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
    return boxes


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


class Index:
    def __init__(self, docs):
        self.docs = Path(docs)
        self.cache = {}

    def domain(self, name):
        if name not in self.cache:
            d = self.docs / name
            if not (d / "domain.json").exists():
                self.cache[name] = None
            else:
                sot_ids = set()
                for s in read_json(d / "screens.json", {}).get("screens", []):
                    sot_ids |= {m.get("id") for m in s.get("markers", [])} | {o.get("id") for o in s.get("offscreen", [])}
                tasks = {}
                for f in (d / "tasks").glob("*.json"):
                    t = read_json(f)
                    ids = set()
                    collect_ids(t.get("stages", {}), ids)
                    for r in ((t.get("stages") or {}).get("grill") or {}).get("rounds", []):
                        ids.add(r["id"])
                        ids |= {f"{r['id']}-{q['id']}" for q in r.get("questions", [])}
                    tasks[t["id"]] = ids
                self.cache[name] = (sot_ids, tasks)
        return self.cache[name]

    def exists(self, domain, task, item):
        d = self.domain(domain)
        if d is None:
            return False
        sot_ids, tasks = d
        if task is None:
            return item in sot_ids
        if task not in tasks:
            return False
        return item is None or item in tasks[task]


def collect_ids(node, out):
    if isinstance(node, dict):
        if isinstance(node.get("id"), str):
            out.add(node["id"])
        for v in node.values():
            collect_ids(v, out)
    elif isinstance(node, list):
        for v in node:
            collect_ids(v, out)


def check_domain(d, index, problems):
    name = d.name
    info = read_json(d / "domain.json")
    if not info.get("title"):
        problems.append(f"{name}/domain.json: title이 없어요")
    kinds = KINDS.get(info.get("kind", "screens"))
    if kinds is None:
        problems.append(f"{name}/domain.json: kind는 {' / '.join(KINDS)} 중 하나")
        kinds = KINDS["screens"]
    sot = read_json(d / "screens.json", {"screens": []})
    seen = set()
    for s in sot.get("screens", []):
        for key in ("id", "title", "image", "metadata"):
            if not s.get(key):
                problems.append(f"{name}/screens.json 화면 {s.get('id', '?')}: {key}가 없어요")
        boxes = {}
        meta = d / s.get("metadata", "")
        if s.get("metadata") and meta.exists():
            boxes = frame_boxes(meta)
        elif s.get("metadata"):
            problems.append(f"{name}/screens.json 화면 {s.get('id')}: 구조 파일이 없어요 ({s['metadata']})")
        if s.get("image") and not (d / s["image"]).exists():
            problems.append(f"{name}/screens.json 화면 {s.get('id')}: 이미지가 없어요 ({s['image']})")
        for m in s.get("markers", []):
            mid = m.get("id", "")
            if not re.fullmatch(r"S\d+", mid):
                problems.append(f"{name}/screens.json: 마커 ID는 S + 번호여야 해요 ({mid or m.get('title')})")
            if mid in seen:
                problems.append(f"{name}/screens.json: 마커 ID {mid}가 겹쳐요")
            seen.add(mid)
            if m.get("kind") not in kinds:
                problems.append(f"{name}/screens.json {mid}: 이 도메인의 kind는 {'/'.join(kinds)} 중 하나")
            if "node" in m and boxes and m["node"] not in boxes:
                problems.append(f"{name}/screens.json {mid}: 구조 파일에 없는 노드 {m['node']} — merge-xml로 컴포넌트 안쪽을 합쳤는지 확인")
            if "node" not in m and not ("x" in m and "y" in m):
                problems.append(f"{name}/screens.json {mid}: node 또는 x · y가 있어야 해요")
        for o in s.get("offscreen", []):
            oid = o.get("id", "")
            if not re.fullmatch(r"X\d+", oid) or oid in seen:
                problems.append(f"{name}/screens.json: 화면 밖 상태 ID {oid or o.get('state')}가 X + 번호가 아니거나 겹쳐요")
            seen.add(oid)
    walk_refs(sot, None, lambda raw, owner: check_ref(raw, name, None, index, problems, f"{name}/screens.json"))
    for f in sorted((d / "tasks").glob("*.json")):
        check_task(f, name, index, problems)


def check_ref(raw, domain, task, index, problems, where):
    dom, t, item = parse_ref(raw, domain, task)
    if t is None and item and not re.fullmatch(r"[SX]\d+", item):
        problems.append(f"{where}: [[{raw}]] — 작업 밖에서는 작업 ID를 붙여요 (예: [[COMP-1#{item}]])")
    elif not index.exists(dom, t, item):
        problems.append(f"{where}: [[{raw}]]가 가리키는 것이 없어요")


def check_task(f, domain, index, problems):
    rel = f"{domain}/tasks/{f.name}"
    t = read_json(f)
    if t.get("id") != f.stem:
        problems.append(f"{rel}: id({t.get('id')})가 파일 이름과 달라요")
    if not t.get("title"):
        problems.append(f"{rel}: title이 없어요")
    stages = t.get("stages") or {}
    if not stages:
        problems.append(f"{rel}: 단계가 하나도 없어요 — flow.py add로 만들어요")
    for k, st in stages.items():
        if k not in STAGES:
            problems.append(f"{rel}: 없는 단계 {k}")
            continue
        if k == "grill":
            for r in st.get("rounds", []):
                for q in r.get("questions", []):
                    tag = f"{r.get('id')}-{q.get('id')}"
                    a = q.get("answer") or {}
                    if a.get("choice") not in (None, "", "unsure") and not q.get("decision") and a.get("by") != "user":
                        problems.append(f"{rel} {tag}: 답은 있는데 결정 문장이 없어요")
                    if q.get("decision") and not q.get("appliedTo"):
                        problems.append(f"{rel} {tag}: 결정을 어디에 반영했는지(appliedTo)가 없어요")
            continue
        for b in st.get("blocks", []):
            if b.get("type") == "table":
                n = len(b.get("columns", []))
                bad = [i + 1 for i, r in enumerate(b.get("rows", [])) if len(r) != n]
                if bad:
                    problems.append(f"{rel} {k} 표 '{b.get('title', '')}': 칸 수가 머리글({n})과 다른 행 {bad}")
        if st.get("status") not in STATUSES:
            problems.append(f"{rel} {k}: status는 {'/'.join(STATUSES)} 중 하나")
        if st.get("status") == "done" and not st.get("conclusion"):
            problems.append(f"{rel} {k}: 완료인데 결론 문장이 없어요")
    now = [k for k, st in stages.items() if k != "grill" and st.get("status") == "now"]
    if len(now) > 1:
        problems.append(f"{rel}: 진행 중(now) 단계가 둘 이상이에요: {', '.join(now)}")
    ids = []

    def gather(node):
        if isinstance(node, dict):
            if isinstance(node.get("id"), str) and ITEM_ID.match(node["id"]):
                ids.append(node["id"])
            for v in node.values():
                gather(v)
        elif isinstance(node, list):
            for v in node:
                gather(v)

    gather({k: v for k, v in stages.items() if k != "grill"})
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        problems.append(f"{rel}: ID가 겹쳐요: {', '.join(dup)}")
    walk_refs(stages, None, lambda raw, owner: check_ref(raw, domain, t.get("id"), index, problems, rel))
    marks = list(user_marks(t))
    if marks:
        problems.append(f"{rel}: 사람이 바꾼 것 {len(marks)}건을 아직 처리하지 않았어요 — flow.py changes")


def cmd_check(args):
    docs, doms = scope(args.target)
    index = Index(docs)
    problems = []
    if not (docs / ".flow/server.mjs").exists():
        problems.append(f"{docs}/.flow가 없어요 — flow.py install {docs}")
    for d in doms:
        check_domain(d, index, problems)
    if problems:
        print(f"문제 {len(problems)}건")
        for p in problems:
            print(f"- {p}")
        sys.exit(1)
    print(f"문제 없음 — 도메인 {len(doms)}")


# ---------------------------------------------------------------- merge-xml

def cmd_merge_xml(args):
    base = ET.parse(args.base)
    index = {el.get("id"): el for el in base.iter()}
    parents = {child: parent for parent in base.iter() for child in parent}
    for path in args.expanded:
        exp = ET.parse(path).getroot()
        target = index.get(exp.get("id"))
        if target is None:
            sys.exit(f"{path}: 바탕 XML에 노드 {exp.get('id')}가 없어요")
        if target is base.getroot():
            sys.exit("화면 프레임 자체는 합칠 수 없어요")
        exp.set("x", target.get("x", "0"))
        exp.set("y", target.get("y", "0"))
        parent = parents[target]
        parent[list(parent).index(target)] = exp
        index = {el.get("id"): el for el in base.iter()}
        parents = {child: parent for parent in base.iter() for child in parent}
    base.write(args.out, encoding="unicode")
    print(f"합쳤어요: {args.out}")


def main():
    ap = argparse.ArgumentParser(description="flow documents tool")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("install")
    p.add_argument("docs")
    p.set_defaults(fn=cmd_install)
    p = sub.add_parser("find")
    p.add_argument("docs")
    p.add_argument("--node")
    p.add_argument("--name")
    p.add_argument("--path")
    p.set_defaults(fn=cmd_find)
    p = sub.add_parser("domain")
    p.add_argument("docs")
    p.add_argument("id")
    p.add_argument("--title", required=True)
    p.add_argument("--kind", choices=list(KINDS), default="screens")
    p.add_argument("--figma")
    p.add_argument("--node", action="append")
    p.add_argument("--path", action="append")
    p.set_defaults(fn=cmd_domain)
    p = sub.add_parser("task")
    p.add_argument("domain")
    p.add_argument("id")
    p.add_argument("--title", required=True)
    p.add_argument("--type", default="기능 개발")
    p.add_argument("--branch")
    p.add_argument("--stages", default="tasks", help="comma-separated: " + ",".join(STAGES))
    p.set_defaults(fn=cmd_task)
    p = sub.add_parser("add")
    p.add_argument("task")
    p.add_argument("stages", nargs="+")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("brief")
    p.add_argument("task")
    p.add_argument("--stage", choices=STAGES)
    p.set_defaults(fn=cmd_brief)
    for name, fn in (("changes", cmd_changes), ("check", cmd_check)):
        p = sub.add_parser(name)
        p.add_argument("target")
        p.set_defaults(fn=fn)
    p = sub.add_parser("clear")
    p.add_argument("file")
    p.add_argument("--id", action="append")
    p.set_defaults(fn=cmd_clear)
    p = sub.add_parser("merge-xml")
    p.add_argument("base")
    p.add_argument("expanded", nargs="+")
    p.add_argument("-o", "--out", required=True)
    p.set_defaults(fn=cmd_merge_xml)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
