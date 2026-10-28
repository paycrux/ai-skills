"""Set up, render and check /flow documents.

    python3 flow.py find <docs> [--node ID] [--name TEXT] [--path PATH]
    python3 flow.py domain <docs> <domain-id> --title "..." [--kind screens|components] [--figma "..."] [--node ID]... [--path PATH]...
    python3 flow.py task <docs>/<domain> <task-id> --title "..." [--type "..."] [--stages plan,screen,tasks]
    python3 flow.py add <docs>/<domain>/tasks/<task>.json <stage>...
    python3 flow.py build <docs>                            write every HTML page from the JSON
    python3 flow.py pull <docs> [--clipboard]               answers the person typed in the pages → JSON ("by": "user")
    python3 flow.py brief <docs>/<domain>/tasks/<task>.json [--stage KEY]   what Claude reads to resume
    python3 flow.py changes <docs | docs/domain>            what the person changed ("by": "user")
    python3 flow.py clear <file.json> [--id ID]...            drop "by": "user" once handled
    python3 flow.py check <docs | docs/domain>
    python3 flow.py migrate <docs> [--apply] [--v1 <old-task-dir> --domain ID [--title "..."] [--keep]]
    python3 flow.py merge-xml <base.xml> <expanded.xml>... -o <out.xml>

Layout:

    <docs>/index.html            every domain (generated)
    <docs>/<domain>/
      domain.json                title, figma, nodes, paths, links
      screens.json               SOT map of the domain's screens (markers S1…, off-screen states X1…)
      tasks/<task-id>.json       one per task: stages plan · screen · grill · tasks · verify · done
      images/                    Figma screenshots and structure XML
      index.html                 domain page: tasks + SOT map (generated)
      <task-id>/                 index.html + 01-plan.html … 06-done.html (generated)

Everything else under <docs> is legacy: listed on the root page, never written.
Standard library only, Python 3.9+.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import browser  # noqa: E402
import migrate  # noqa: E402
import render  # noqa: E402
from model import (ITEM_ID, KINDS, RESERVED_TASK_IDS, STAGE_KEYS, STATUSES, frame_boxes, git, parse_ref,  # noqa: E402
                   plain, read_json, scope, task_files, task_items, walk_refs, write_json)


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
    bad = [k for k in keys if k not in STAGE_KEYS]
    if bad:
        sys.exit(f"없는 단계: {', '.join(bad)} — {' · '.join(STAGE_KEYS)} 중에서")
    return keys


def docs_of(target):
    docs, _ = scope(target)
    return docs


# ---------------------------------------------------------------- domain / task

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
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", args.id) or args.id.lower() in RESERVED_TASK_IDS:
        sys.exit("작업 ID는 지라 키(APP-452)나 짧은 영어 이름(bug-bottom-inset)으로 — tasks · images · index는 쓸 수 없어요")
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
    task["stages"] = {k: task["stages"][k] for k in STAGE_KEYS if k in task["stages"]}
    write_json(args.task, task)
    print(f"추가했어요: {', '.join(made) if made else '이미 다 있어요'}")


# ---------------------------------------------------------------- build / pull

def cmd_build(args):
    docs = docs_of(args.target)
    server, v1 = migrate.detect(docs)
    site, total, written, removed = render.build(docs)
    print(f"HTML {total}쪽 — 새로 쓴 것 {written}" + (f", 지운 것 {len(removed)}" if removed else ""))
    print(f"열기: {(site.docs / site.root).resolve()}")
    if server or v1:
        print("이전 버전 문서가 남아 있어요 — flow.py migrate " + str(docs))


def cmd_pull(args):
    docs = docs_of(args.target)
    pulled = []
    if args.clipboard:
        parsed = browser.parse_copied(browser.read_clipboard())
        if not parsed:
            sys.exit("클립보드에 flow 답이 없어요 — 페이지에서 '답 복사'를 한 번 더 눌러 주세요")
        d, t, state = parsed
        pulled.append((d, t, state, "클립보드"))
    else:
        for tag, (state, label) in sorted(browser.browser_answers(docs).items()):
            d, t = tag.split("/", 1)
            pulled.append((d, t, state, label))
    if not pulled:
        print("브라우저에 저장된 답이 없어요.\n"
              "- 방금 입력했다면 10초쯤 뒤에 다시 해요 (브라우저가 디스크에 쓰는 데 몇 초 걸려요)\n"
              "- Safari · Firefox에서 입력했다면 페이지의 '답 복사'를 누르게 하고 flow.py pull --clipboard")
        return
    any_change = False
    for d, t, state, label in pulled:
        path = docs / d / "tasks" / f"{t}.json"
        if not path.exists():
            print(f"{d}/{t}: 작업 파일이 없어서 건너뜀 ({label})")
            continue
        task = read_json(path)
        if int(state.get("updatedAt") or 0) <= int(task.get("pulledAt") or 0):
            print(f"{d}/{t}: 이미 반영한 답이에요 ({label})")
            continue
        lines = browser.merge(task, state)
        write_json(path, task)
        print(f"{d}/{t} ← {label}" + ("" if lines else " · 바뀐 것 없음"))
        for line in lines:
            print(f"- {line}")
        any_change = any_change or bool(lines)
    if any_change:
        print(f"\n다음: flow.py changes {docs} → 처리 → clear → build")


# ---------------------------------------------------------------- brief

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
    for k in STAGE_KEYS:
        if k in stages:
            print("  " + stage_line(k, stages[k]))
    keys = [args.stage] if args.stage else [k for k in STAGE_KEYS if k in stages]
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
        elif not node.get("choice") and not node.get("note") and not node.get("copy"):
            lines.append(f"{tag}: 사람이 답을 지움 — 결정을 되돌릴지 물어요")
        else:
            note = (f" · 문구 \"{node['copy']}\"" if node.get("copy") else "") + (f" · 메모 \"{node['note']}\"" if node.get("note") else "")
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
        for f in [d / "domain.json", d / "screens.json", *task_files(d)]:
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
        print("\n처리한 뒤: flow.py clear <파일> [--id …] → flow.py build " + str(docs))


def cmd_clear(args):
    data = read_json(args.file)
    ids = set(args.id or [])
    for trail, node in list(user_marks(data)):
        names = {node.get("id"), question_tag(trail) if "choice" in node else None, trail[-1] if trail else None}
        if not ids or names & ids:
            del node["by"]
    write_json(args.file, data)
    left = len(list(user_marks(data)))
    print(f"정리했어요: {args.file}" + (f" — 남은 표시 {left}" if left else ""))


# ---------------------------------------------------------------- check

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
                for f in task_files(d):
                    t = read_json(f)
                    tasks[t["id"]] = set(task_items(t))
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
            boxes = frame_boxes(meta)[2]
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
            if m.get("node") and boxes and m["node"] not in boxes:
                problems.append(f"{name}/screens.json {mid}: 구조 파일에 없는 노드 {m['node']} — merge-xml로 컴포넌트 안쪽을 합쳤는지 확인")
            if not m.get("node") and not ("x" in m and "y" in m):
                problems.append(f"{name}/screens.json {mid}: node 또는 x · y가 있어야 해요")
        for o in s.get("offscreen", []):
            oid = o.get("id", "")
            if not re.fullmatch(r"X\d+", oid) or oid in seen:
                problems.append(f"{name}/screens.json: 화면 밖 상태 ID {oid or o.get('state')}가 X + 번호가 아니거나 겹쳐요")
            seen.add(oid)
    walk_refs(sot, None, lambda raw, owner: check_ref(raw, name, None, index, problems, f"{name}/screens.json"))
    for f in task_files(d):
        check_task(f, name, index, problems)


def check_ref(raw, domain, task, index, problems, where):
    dom, t, item = parse_ref(raw, domain, task)
    if t is None and item and not re.fullmatch(r"[SX]\d+", item):
        problems.append(f"{where}: [[{raw}]] — 작업 밖에서는 작업 ID를 붙여요 (예: [[APP-1#{item}]])")
    elif not index.exists(dom, t, item):
        problems.append(f"{where}: [[{raw}]]가 가리키는 것이 없어요")


def check_task(f, domain, index, problems):
    rel = f"{domain}/tasks/{f.name}"
    t = read_json(f)
    if t.get("id") != f.stem:
        problems.append(f"{rel}: id({t.get('id')})가 파일 이름과 달라요")
    if str(t.get("id", "")).lower() in RESERVED_TASK_IDS:
        problems.append(f"{rel}: 작업 ID로 tasks · images · index는 쓸 수 없어요")
    if not t.get("title"):
        problems.append(f"{rel}: title이 없어요")
    stages = t.get("stages") or {}
    if not stages:
        problems.append(f"{rel}: 단계가 하나도 없어요 — flow.py add로 만들어요")
    for k, st in stages.items():
        if k not in STAGE_KEYS:
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
    server, v1 = migrate.detect(docs)
    if server or v1:
        problems.append(f"이전 버전 flow 문서가 있어요 ({', '.join(p.name for p in server + v1)}) — flow.py migrate {docs}")
    for d in doms:
        check_domain(d, index, problems)
    problems += [f"HTML: {s} — flow.py build {docs}" for s in render.stale(docs)]
    if problems:
        print(f"문제 {len(problems)}건")
        for p in problems:
            print(f"- {p}")
        sys.exit(1)
    print(f"문제 없음 — 도메인 {len(doms)}")


# ---------------------------------------------------------------- migrate

def cmd_migrate(args):
    docs = Path(args.docs)
    if args.v1:
        if not args.domain:
            sys.exit("--v1에는 --domain이 필요해요 — flow.py find로 맞는 도메인을 먼저 찾아요")
        for line in migrate.convert_v1(docs, args.v1, args.domain, args.title, args.keep):
            print(line)
        render.build(docs)
        print(f"HTML을 다시 만들었어요 — 다음: flow.py check {docs}")
        return
    server, v1 = migrate.detect(docs)
    if not server and not v1:
        print("옮길 이전 버전 문서가 없어요")
        return
    if server and not args.apply:
        print("이전 로컬 서버 방식의 파일이에요. 아직 지우지 않았어요:")
        for line in migrate.plan_server(docs):
            print(line)
        root = render.Site(docs).root
        print(f"같은 문서는 서버 없이 {docs / root} 와 {docs}/<도메인>/index.html 에서 열려요")
        print(f"사용자에게 위 목록과 새 경로를 알리고 확인받은 뒤: flow.py migrate {docs} --apply")
    elif server:
        for line in migrate.clean_server(docs):
            print(line)
    for d in v1:
        sot = read_json(d / "data" / "sot.json", {})
        nodes = [s.get("figma", "").split()[0] for s in sot.get("screens", []) if s.get("figma")]
        hint = ""
        for n in nodes:
            for dom in sorted(p for p in docs.iterdir() if (p / "domain.json").exists()):
                if n in json.dumps(read_json(dom / "screens.json", {}), ensure_ascii=False) or n in read_json(dom / "domain.json").get("nodes", []):
                    hint = f" — 노드 {n}가 도메인 {dom.name}에 있어요"
        title = read_json(d / "data" / "task.json").get("title", d.name)
        print(f"v1 작업 폴더: {d.name} ({title}){hint}\n  옮기기: flow.py migrate {docs} --v1 {d} --domain <도메인 ID> [--title \"<새 도메인 이름>\"]")
    site, total, written, removed = render.build(docs)
    print(f"HTML {total}쪽을 다시 만들었어요")


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
    p.add_argument("--stages", default="tasks", help="comma-separated: " + ",".join(STAGE_KEYS))
    p.set_defaults(fn=cmd_task)
    p = sub.add_parser("add")
    p.add_argument("task")
    p.add_argument("stages", nargs="+")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("build")
    p.add_argument("target")
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("pull")
    p.add_argument("target")
    p.add_argument("--clipboard", action="store_true")
    p.set_defaults(fn=cmd_pull)
    p = sub.add_parser("brief")
    p.add_argument("task")
    p.add_argument("--stage", choices=STAGE_KEYS)
    p.set_defaults(fn=cmd_brief)
    for name, fn in (("changes", cmd_changes), ("check", cmd_check)):
        p = sub.add_parser(name)
        p.add_argument("target")
        p.set_defaults(fn=fn)
    p = sub.add_parser("clear")
    p.add_argument("file")
    p.add_argument("--id", action="append")
    p.set_defaults(fn=cmd_clear)
    p = sub.add_parser("migrate")
    p.add_argument("docs")
    p.add_argument("--v1")
    p.add_argument("--domain")
    p.add_argument("--title")
    p.add_argument("--keep", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(fn=cmd_migrate)
    p = sub.add_parser("merge-xml")
    p.add_argument("base")
    p.add_argument("expanded", nargs="+")
    p.add_argument("-o", "--out", required=True)
    p.set_defaults(fn=cmd_merge_xml)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
