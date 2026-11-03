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
    python3 flow.py export <docs>/<domain>/tasks/<task>.json --to plan|backend --format html|md [-o FILE] [--copy]
    python3 flow.py migrate <docs> [--apply] [--v1 <old-task-dir> --domain ID [--title "..."] [--keep]]
    python3 flow.py merge-xml <base.xml> <expanded.xml>... -o <out.xml>
    python3 flow.py routes <task.json> [--src DIR]          route · sheet rows for the files the task names (task route map)
    python3 flow.py open <page.html>                        build, then open the page in the OS default browser
    python3 flow.py current [<dir>]                         the flow task whose branch is the checked-out one (SessionStart hook)
    python3 flow.py log <docs> --file PATH... -m "..." [--sha SHA] [--task ID]   one follow-up line on the task that covers the files
    python3 flow.py prune <task.json>                       a finished task keeps conclusions and decisions only
    python3 flow.py feature <docs> <feature-id> --title "..." --root BRANCH [--prd URL]   a feature document skeleton
    python3 flow.py start <docs>/features/<id>/feature.json [--row KEY]... [--approve] [--dry-run]
    python3 flow.py jira <task.json> start|done [--dry-run]  walk the Jira issue one transition at a time; done also comments

Layout:

    <docs>/index.html            every domain (generated)
    <docs>/features/<id>/        feature.json, prd.md snapshot, issues/*.md, index.html (generated)
    <docs>/<domain>/
      domain.json                title, figma, nodes, paths, links
      screens.json               SOT map of the domain's screens (markers S1…, off-screen states X1…)
      tasks/<task-id>.json       one per task: stages plan · screen · grill · tasks · verify · done
      images/                    Figma screenshots and structure XML
      diagrams/                  Archify flow diagrams (<task>-<slug>.json + .html), shown by "diagram" blocks
      index.html                 domain page: tasks + SOT map (generated)
      <task-id>/                 index.html + 01-plan.html … 05-done.html (generated)
        share/                   plan.html · plan.md · backend.html · backend.md, copies to send outside (generated)

Everything else under <docs> is legacy: listed on the root page, never written.
Standard library only, Python 3.9+.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import browser  # noqa: E402
import feature as feat  # noqa: E402
import migrate  # noqa: E402
import render  # noqa: E402
import share  # noqa: E402
from model import (ITEM_ID, KINDS, RESERVED_TASK_IDS, STAGE_KEYS, STATUSES, domains_of, frame_boxes, git,  # noqa: E402
                   parse_ref, plain, read_json, scope, stage_skeleton, task_files, task_items, task_state, walk_refs,
                   write_json)


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
    if args.path:
        for name, task, f in tasks_naming(doms, [args.path]):
            print(f"  작업 {name}/{task['id']} ({task.get('title', '')}) — {STATE_WORD[task_state(task)]}: {f}")


STATE_WORD = {"done": "끝남", "now": "진행 중", "ask": "답 대기", "wait": "시작 전"}


def tasks_naming(doms, paths):
    """Tasks whose JSON names one of the paths (or a file under it)."""
    out = []
    for d in doms:
        for f in task_files(d):
            text = f.read_text()
            if any(p.strip().rstrip("/") and p.strip().rstrip("/") in text for p in paths):
                out.append((d.name, json.loads(text), f))
    return out


def cmd_domain(args):
    docs = Path(args.docs)
    root = docs / args.id
    if (root / "domain.json").exists():
        sys.exit(f"이미 있는 도메인이에요: {root} — 작업은 flow.py task로 추가해요")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.id) or args.id == feat.FEATURES:
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
    tracked = tracked_generated(docs)
    if tracked:
        print(f"커밋된 생성물 {len(tracked)}개 — git에서 빼려면 flow.py migrate {docs} --apply")
    if server or v1:
        print("이전 버전 문서가 남아 있어요 — flow.py migrate " + str(docs))


def cmd_export(args):
    path, n, text = share.export(args.task, args.to, args.format, args.out)
    print(f"{share.AUDIENCES[args.to]} 공유본 · {'HTML' if args.format == 'html' else '텍스트'} · 보낼 것 {n}건")
    print(f"파일: {path.resolve()}")
    if args.copy:
        try:
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            print("클립보드에 복사했어요")
        except (OSError, subprocess.CalledProcessError):
            print("클립보드에 복사하지 못했어요 — 파일을 열어 복사해 주세요")


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


def brief_head(t):
    stages = t.get("stages", {})
    lines = [f"{t['id']} {t['title']} · {t.get('type', '')} · {t.get('branch', '')}"]
    lines += ["  " + stage_line(k, stages[k]) for k in STAGE_KEYS if k in stages]
    return lines


def cmd_brief(args):
    t = read_json(args.task)
    stages = t.get("stages", {})
    for line in brief_head(t):
        print(line)
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
        mids = {m.get("id") for m in s.get("markers", [])}
        for a in s.get("apis") or []:
            for r in a.get("rows", []):
                bad = [i for i in r.get("to") or [] if i not in mids]
                if bad:
                    problems.append(f"{name}/screens.json 화면 {s.get('id')} API {a.get('call', '?')} {r.get('field', '?')}: 이 화면에 없는 마커 {', '.join(bad)}")
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
        problems.append(f"{rel}: 작업 ID로 tasks · images · diagrams · index는 쓸 수 없어요")
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
            if b.get("type") == "diagram" and not (f.parent.parent / str(b.get("src", ""))).is_file():
                problems.append(f"{rel} {k} 흐름도 '{b.get('title', '')}': 파일 {b.get('src', '')}이 없어요")
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


def check_feature(fd, problems):
    rel = f"{feat.FEATURES}/{fd.name}/feature.json"
    f = read_json(fd / "feature.json")
    for key in ("title", "root"):
        if not f.get(key):
            problems.append(f"{rel}: {key}가 없어요")
    for p in f.get("prd") or []:
        if p.get("snapshot") and not (fd / p["snapshot"]).is_file():
            problems.append(f"{rel}: 기획서 스냅샷 {p['snapshot']}이 없어요")
    seen = set()
    for r in f.get("rows", []):
        k = feat.row_key(r)
        if not k:
            problems.append(f"{rel}: id도 issue도 없는 줄이 있어요 ({r.get('title', '?')})")
        if k in seen:
            problems.append(f"{rel}: 줄 {k}가 겹쳐요")
        seen.add(k)
        if not r.get("legacy"):
            for key in ("story", "title", "domain"):
                if not r.get(key):
                    problems.append(f"{rel} {k}: {key}가 없어요")
            if r.get("approved") and not r.get("issue") and not (fd / (r.get("issueBody") or "")).is_file():
                problems.append(f"{rel} {k}: 만들 이슈의 issueBody 파일이 없어요")
    steps = (f.get("jira") or {}).get("path") or []
    marks = [s.get("mark") for s in steps if s.get("mark")]
    if steps and ("start" not in marks or "done" not in marks):
        problems.append(f"{rel}: jira.path에 \"mark\": \"start\"와 \"done\" 단계가 있어야 해요")


def cmd_check(args):
    docs, doms = scope(args.target)
    index = Index(docs)
    problems = []
    server, v1 = migrate.detect(docs)
    if server or v1:
        problems.append(f"이전 버전 flow 문서가 있어요 ({', '.join(p.name for p in server + v1)}) — flow.py migrate {docs}")
    for d in doms:
        check_domain(d, index, problems)
    for fd in feat.feature_dirs(docs):
        check_feature(fd, problems)
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
    tracked = tracked_generated(docs)
    if tracked and args.apply:
        top = git(docs, "rev-parse", "--show-toplevel")
        subprocess.run(["git", "-C", top, "rm", "--cached", "-q", "--", *tracked], check=False)
        print(f"커밋돼 있던 생성물 {len(tracked)}개를 git에서 뺐어요 (파일은 그대로) — 다음 커밋에 함께 들어가요")
    elif tracked:
        print(f"커밋된 생성물 {len(tracked)}개 — 이제 생성물은 커밋하지 않아요. 사용자에게 알리고 flow.py migrate {docs} --apply")
        for t in tracked[:8]:
            print(f"  {t}")
        if len(tracked) > 8:
            print(f"  … 외 {len(tracked) - 8}개")
    if not server and not v1:
        if not tracked:
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


# ---------------------------------------------------------------- generated files stay out of git

def tracked_generated(docs):
    top = git(docs, "rev-parse", "--show-toplevel")
    if not top:
        return []
    files = git(top, "ls-files", "--", str(Path(docs).resolve())).splitlines()
    out = []
    for f in files:
        p = Path(top) / f
        if "/share/" in f or "/.receipts/" in f or (p.suffix == ".html" and render.is_generated(p)):
            out.append(f)
    return out


# ---------------------------------------------------------------- open / current

def docs_above(path):
    for parent in Path(path).resolve().parents:
        if domains_of_safe(parent) or (parent / feat.FEATURES).is_dir():
            top = parent
            for up in parent.parents:
                if domains_of_safe(up) or (up / feat.FEATURES).is_dir():
                    top = up
            return top
    return None


def domains_of_safe(p):
    try:
        return p.is_dir() and bool(domains_of(p))
    except OSError:
        return False


def cmd_open(args):
    page = Path(args.page)
    docs = docs_above(page)
    if docs is None:
        sys.exit(f"flow 문서 폴더를 찾지 못했어요: {page}")
    render.build(docs)
    if not page.exists():
        sys.exit(f"build 뒤에도 없는 페이지예요: {page}")
    opener = {"darwin": ["open"], "win32": ["cmd", "/c", "start", ""]}.get(sys.platform, ["xdg-open"])
    if os.environ.get("SSH_CONNECTION") or (sys.platform.startswith("linux") and not os.environ.get("DISPLAY")):
        print(f"열 수 없는 환경이에요 — 경로: {page.resolve()}")
        return
    subprocess.run([*opener, str(page.resolve())], check=False)
    print(f"열었어요: {page.resolve()}")


def cmd_current(args):
    try:
        here = Path(args.dir or ".").resolve()
        top = Path(git(here, "rev-parse", "--show-toplevel") or here)
        docs = top / "docs"
        if not docs.is_dir():
            return
        doms = domains_of(docs)
        if not doms:
            return
        branch = git(top, "branch", "--show-current")
        hits = []
        for d in doms:
            for f in task_files(d):
                try:
                    t = json.loads(f.read_text())
                except ValueError:
                    continue
                if branch and t.get("branch") == branch:
                    hits.append((f, t))
        if not hits:
            print("이 브랜치에 맞는 flow 작업이 없음")
        elif len(hits) > 1:
            print("여러 개: " + ", ".join(t["id"] for _, t in hits))
        else:
            f, t = hits[0]
            for line in brief_head(t):
                print(line)
            print(f"  작업 파일: {f.relative_to(top)}")
    except Exception:  # noqa: BLE001 — a hook must never break session start
        return


# ---------------------------------------------------------------- follow-up log / prune

def cmd_log(args):
    docs, doms = scope(args.docs)
    if args.task:
        hits = [(d.name, read_json(f), f) for d in doms for f in task_files(d) if f.stem == args.task]
    else:
        hits = tasks_naming(doms, args.file)
    if not hits:
        print("이 파일을 다룬 flow 작업이 없어요 — 커밋 메시지가 기록이에요")
        return
    if len(hits) > 1:
        print("이 파일을 다룬 작업이 여럿이에요 — --task로 하나를 골라요:")
        for name, t, _ in hits:
            print(f"  {name}/{t['id']} {t.get('title', '')}")
        sys.exit(1)
    name, task, f = hits[0]
    sha = args.sha or git(f.parent, "rev-parse", "--short", "HEAD")
    task.setdefault("followUps", []).append({"date": date.today().isoformat(), "text": args.message,
                                             "files": args.file or [], "sha": sha})
    write_json(f, task)
    render.build(docs)
    print(f"{name}/{task['id']}에 후속 수정 한 줄을 남겼어요 ({sha})")


KEEP_Q = ("id", "title", "decision", "appliedTo", "to")
KEEP_ROWS = ("결정", "파일")


def cmd_prune(args):
    task = read_json(args.task)
    if task_state(task) != "done":
        sys.exit(f"{task['id']}: 아직 끝나지 않은 작업이에요 — 모든 단계가 done일 때만 정리해요")
    stages = task.get("stages") or {}
    dropped = 0
    for r in (stages.get("grill") or {}).get("rounds", []):
        for q in r.get("questions", []):
            for k in [k for k in q if k not in KEEP_Q]:
                del q[k]
                dropped += 1
    for key, st in stages.items():
        if key == "grill":
            continue
        for b in st.get("blocks", []):
            if b.get("type") != "checklist":
                continue
            for it in b.get("items", []):
                keep = [r for r in it.get("rows", []) if r and r[0] in KEEP_ROWS]
                dropped += len(it.get("rows", [])) - len(keep)
                if keep:
                    it["rows"] = keep
                else:
                    it.pop("rows", None)
    task.pop("pulledAt", None)
    task["pruned"] = date.today().isoformat()
    write_json(args.task, task)
    print(f"{task['id']}: 세부 {dropped}개를 정리했어요 — 결론 · 결정 · 결정 행은 남김. 전체 기록은 git에 있어요")
    print(f"다음: flow.py check {Path(args.task).resolve().parent.parent}")


# ---------------------------------------------------------------- feature / start / jira

def cmd_feature(args):
    root = Path(args.docs) / feat.FEATURES / args.id
    if (root / "feature.json").exists():
        sys.exit(f"이미 있는 기능 문서예요: {root / 'feature.json'}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.id):
        sys.exit("기능 ID는 영어 소문자 · 숫자 · 하이픈으로 (예: gift, account-settings)")
    (root / "issues").mkdir(parents=True, exist_ok=True)
    prd = [{"label": "기획서", "url": args.prd, "snapshot": "prd.md", "lastEdited": ""}] if args.prd else []
    write_json(root / "feature.json", {
        "id": args.id, "title": args.title, "root": args.root, "repo": feat.common_repo(args.docs),
        "prd": prd, "links": [], "scope": [],
        "jira": {"project": "", "issueType": "[개발]", "site": "", "path": []},
        "rows": [], "copy": [], "shared": [], "componentDiffs": [], "questions": [], "log": []})
    print(f"기능 문서를 만들었어요: {root / 'feature.json'}")


def cmd_start(args):
    try:
        lines = feat.start(args.feature, args.row, args.approve, args.dry_run)
    except RuntimeError as e:
        print(f"멈춤: {e}\n끝난 단계는 feature.json에 기록됐어요 — 고친 뒤 같은 명령을 다시 실행하면 이어서 해요")
        sys.exit(1)
    for line in lines:
        print(line)
    if not args.dry_run:
        f = Path(args.feature)
        docs = feat.docs_of_feature(f) if f.exists() else None
        if docs and docs.is_dir():
            render.build(docs)


def cmd_jira(args):
    try:
        for line in feat.jira_step(args.task, args.step, args.dry_run):
            print(line)
    except RuntimeError as e:
        sys.exit(f"멈춤: {e}")
    fpath, _ = feat.feature_of(read_json(args.task))
    for docs in {feat.docs_of_feature(fpath) if fpath else None, docs_above(args.task)} - {None}:
        render.build(docs)


# ---------------------------------------------------------------- task route map

ROUTE_EXT = (".tsx", ".ts", ".jsx", ".js")
SHEET = re.compile(r"""openSheet\(\s*['"]([\w-]+)['"]""")


def app_routes(top, src):
    """Every route file under an Expo Router / Next.js app directory → [(path, file)]."""
    base = Path(top) / src if src else next((Path(top) / c for c in ("app", "src/app") if (Path(top) / c).is_dir()), None)
    if base is None or not base.is_dir():
        return []
    files = [p for p in base.rglob("*") if p.suffix in ROUTE_EXT and "node_modules" not in p.parts]
    nextjs = any(p.stem == "page" for p in files)
    out = []
    for p in sorted(files):
        if nextjs and p.stem != "page":
            continue
        if not nextjs and (p.stem.startswith(("_", "+")) or p.stem.endswith((".test", ".spec"))):
            continue
        parts = list(p.relative_to(base).with_suffix("").parts)
        if nextjs or parts[-1] == "index":
            parts = parts[:-1]
        parts = [x for x in parts if not (x.startswith("(") and x.endswith(")"))]
        out.append(("/" + "/".join(parts), p.relative_to(top).as_posix()))
    return out


def cmd_routes(args):
    path = Path(args.task).resolve()
    task = read_json(path)
    top = git(path.parent, "rev-parse", "--show-toplevel")
    if not top:
        sys.exit("git 저장소 안의 작업이 아니에요")
    text = path.read_text()
    domain = read_json(path.parent.parent / "domain.json")
    prefixes = [p.rstrip("/") + "/" for p in domain.get("paths") or [] if p.startswith(("app", "src/app"))]
    named = [(r, f) for r, f in app_routes(top, args.src) if f in text or any(f.startswith(x) for x in prefixes)]
    if not named:
        print("이 작업이 이름을 댄 경로 파일이 없어요 — 항목의 파일 행이나 도메인 paths에 app/ 경로가 있어야 해요")
        return
    stage_key = "screen" if "screen" in task["stages"] else "tasks" if "tasks" in task["stages"] else next(iter(task["stages"]))
    stage = task["stages"][stage_key]
    block = next((b for b in stage.setdefault("blocks", []) if b.get("type") == "routes"), None)
    if block is None:
        block = {"type": "routes", "title": "작업 경로 맵", "rows": []}
        stage["blocks"].insert(0, block)
    old = {r.get("file"): r for r in block.get("rows", [])}
    rows = []
    for route, f in named:
        sheets = sorted(set(SHEET.findall((Path(top) / f).read_text(errors="ignore"))))
        prev = old.get(f, {})
        rows.append({"path": route, "file": f, "name": prev.get("name", ""), "sheets": sheets, "apis": prev.get("apis", [])})
    block["rows"] = rows
    write_json(path, task)
    print(f"{task['id']} {stage_key} 단계에 경로 {len(rows)}개 — 기능 이름과 이 작업에서 확인한 API만 채워요")
    for r in rows:
        print(f"  {r['path']:<28} {r['file']}" + (f"  시트 {', '.join(r['sheets'])}" if r["sheets"] else ""))


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
    p = sub.add_parser("export")
    p.add_argument("task")
    p.add_argument("--to", choices=list(share.AUDIENCES), required=True)
    p.add_argument("--format", choices=["html", "md"], required=True)
    p.add_argument("-o", "--out")
    p.add_argument("--copy", action="store_true")
    p.set_defaults(fn=cmd_export)
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
    p = sub.add_parser("routes")
    p.add_argument("task")
    p.add_argument("--src")
    p.set_defaults(fn=cmd_routes)
    p = sub.add_parser("open")
    p.add_argument("page")
    p.set_defaults(fn=cmd_open)
    p = sub.add_parser("current")
    p.add_argument("dir", nargs="?")
    p.set_defaults(fn=cmd_current)
    p = sub.add_parser("log")
    p.add_argument("docs")
    p.add_argument("--file", action="append", default=[])
    p.add_argument("-m", "--message", required=True)
    p.add_argument("--sha")
    p.add_argument("--task")
    p.set_defaults(fn=cmd_log)
    p = sub.add_parser("prune")
    p.add_argument("task")
    p.set_defaults(fn=cmd_prune)
    p = sub.add_parser("feature")
    p.add_argument("docs")
    p.add_argument("id")
    p.add_argument("--title", required=True)
    p.add_argument("--root", required=True)
    p.add_argument("--prd")
    p.set_defaults(fn=cmd_feature)
    p = sub.add_parser("start")
    p.add_argument("feature")
    p.add_argument("--row", action="append")
    p.add_argument("--approve", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_start)
    p = sub.add_parser("jira")
    p.add_argument("task")
    p.add_argument("step", choices=["start", "done"])
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_jira)
    p = sub.add_parser("merge-xml")
    p.add_argument("base")
    p.add_argument("expanded", nargs="+")
    p.add_argument("-o", "--out", required=True)
    p.set_defaults(fn=cmd_merge_xml)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
