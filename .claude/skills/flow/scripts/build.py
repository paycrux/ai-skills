"""Build, apply, and check a /flow task folder.

    python3 build.py init <task-dir> --title "..." [--key ABC-1] [--type "기능 개발"]
    python3 build.py build <task-dir>
    python3 build.py apply <task-dir>
    python3 build.py tick <task-dir> <stage-file> <item-key> [--undo]
    python3 build.py check <task-dir>
    python3 build.py merge-xml <base.xml> <expanded.xml>... -o <out.xml>

Task folder layout:

    <task-dir>/
      index.html  01-plan.html  02-screen.html  03-grill.html  04-tasks.html  05-verify.html  06-done.html
      data/   task.json  sot.json  grill.json  inbox.json  <screen>.png  <screen>.xml
      assets/ copied from the skill on every build — never edit by hand

Generated from data (never edit the HTML): 02-screen.html, 03-grill.html, index.html, the nav block of every page.
Written by Claude (edit the HTML): 01-plan.html, 04-tasks.html, 05-verify.html, 06-done.html.

Standard library only, Python 3.9+.
"""
import argparse
import html
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
STAGES = [
    ("01-plan.html", "기획"),
    ("02-screen.html", "화면 · SOT 맵"),
    ("03-grill.html", "질문"),
    ("04-tasks.html", "구현 계획 · 구현"),
    ("05-verify.html", "검증"),
    ("06-done.html", "완료"),
]
AUTHORED = ["01-plan.html", "04-tasks.html", "05-verify.html", "06-done.html"]
STATUSES = ("done", "now", "ask", "wait")
KIND = {
    "server": ("Data", "data"),
    "format": ("Computed", "comp"),
    "calc": ("Computed · 계산", "comp"),
    "action": ("Action", "act"),
    "pending": ("확인 필요", "pend"),
    "out": ("범위 제외", "out"),
}
GAP = 14
NAV = re.compile(r"<!-- flow:nav -->.*?<!-- /flow:nav -->", re.S)
CONCLUSION = re.compile(r'<section class="conclusion" data-status="(\w+)" data-summary="([^"]*)">(.*?)</section>', re.S)
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600"
         "&family=IBM+Plex+Sans+KR:wght@400;600;700&display=swap")


def esc(text):
    return html.escape(str(text), quote=True)


def read_json(path, default=None):
    if not path.exists():
        if default is not None:
            return default
        sys.exit(f"없는 파일: {path}")
    return json.loads(path.read_text())


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def shell(task, title, body, css=(), js=(), wide=False):
    links = "".join(f'<link rel="stylesheet" href="assets/{c}">' for c in ("style.css", "nav.css") + tuple(css))
    scripts = "".join(f'<script src="assets/{j}"></script>' for j in ("nav.js", "live.js") + tuple(js))
    return (
        '<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="flow-task" content="{esc(task["id"])}"><title>{esc(title)} · {esc(task["title"])}</title>'
        f'<link rel="stylesheet" href="{FONTS}">{links}</head>\n<body>\n'
        "<!-- flow:nav --><!-- /flow:nav -->\n"
        f'<main class="page{" wide" if wide else ""}">\n{body}\n</main>\n{scripts}\n</body></html>\n'
    )


def conclusion_html(status, summary, items):
    lis = "".join(f"<li>{i}</li>" for i in items)
    return (f'<section class="conclusion" data-status="{status}" data-summary="{esc(summary)}">'
            f"<h2>결론</h2><ul>{lis}</ul></section>")


# ---------------------------------------------------------------- 02 screen

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
    return float(root.get("width")), float(root.get("height")), boxes


def place(marker, width, boxes):
    if "node" not in marker:
        return marker["x"], marker["y"], "좌표 직접 지정"
    x, y, w, h = boxes[marker["node"]]
    right = x + w + GAP
    if marker.get("side") == "left" or right > width - 12:
        return max(12, x - GAP), y + h / 2, f"노드 {marker['node']} 왼쪽"
    return right, y + h / 2, f"노드 {marker['node']} 오른쪽"


def build_screen(root, task):
    sot = read_json(root / "data/sot.json")
    parts = []
    for flow in sot.get("flows", []):
        rows = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in flow["rows"])
        parts.append(f'<h2>흐름 · {flow["title"]}</h2><table><thead><tr><th>언제</th><th>결과</th></tr></thead><tbody>{rows}</tbody></table>')
    counts, n = {}, 0
    for screen in sot.get("screens", []):
        width, height, boxes = frame_boxes(root / "data" / screen["metadata"])
        missing = [m["node"] for m in screen["markers"] if "node" in m and m["node"] not in boxes]
        if missing:
            sys.exit(f"{screen['metadata']}에 없는 노드: {', '.join(missing)} — merge-xml로 컴포넌트 안쪽을 합쳤는지 확인하세요")
        pins, groups = [], []
        for m in screen["markers"]:
            n += 1
            label, cls = KIND[m["kind"]]
            counts[label] = counts.get(label, 0) + 1
            x, y, how = place(m, width, boxes)
            pins.append(f'<button class="pin k-{cls}" data-i="{n}" title="{esc(how)}" '
                        f'style="left:{x / width * 100:.2f}%;top:{y / height * 100:.2f}%">{n}</button>')
            note = f'<div class="nt">{m["note"]}</div>' if m.get("note") else ""
            row = (f'<tr data-i="{n}"><td><span class="mk k-{cls}">{n}</span></td>'
                   f'<td><b>{m["title"]}</b><br><span class="k {cls}">{label}</span></td>'
                   f'<td>{m.get("field", "—")}</td><td>{m.get("rule", "")}{note}</td></tr>')
            if not groups or groups[-1][0] != m.get("section", "화면 요소"):
                groups.append((m.get("section", "화면 요소"), []))
            groups[-1][1].append(row)
        tables = "".join(
            f"<h3>{s}</h3><table><thead><tr><th></th><th>요소</th><th>서버 필드</th><th>규칙 · 근거</th></tr></thead>"
            f"<tbody>{''.join(r)}</tbody></table>" for s, r in groups)
        off_rows = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>" for a, b, c in screen.get("offscreen", []))
        off = ""
        if off_rows:
            intro = screen.get("offscreenIntro", "Figma 화면에는 없지만 데이터 때문에 생기는 경우예요.")
            off = (f'<h3>화면 밖 상태</h3><p class="note">{intro}</p><table><thead><tr><th>상태</th><th>언제</th>'
                   f"<th>보이는 것</th></tr></thead><tbody>{off_rows}</tbody></table>")
        parts.append(
            f'<h2>화면 · {screen["title"]}</h2><p class="meta">Figma <code>{esc(screen["figma"])}</code></p>'
            f'<div class="cols"><div class="shot"><div class="fig" style="width:{width:.0f}px">'
            f'<img src="data/{esc(screen["image"])}" alt="{esc(screen["title"])} Figma 화면" style="width:{width:.0f}px">{"".join(pins)}</div></div>'
            f"<div>{tables}{off}</div></div>")
    chips = "".join(f"<span>{k} {v}</span>" for k, v in counts.items())
    meta = " · ".join(x for x in (
        f"API <code>{esc(sot['api'])}</code>" if sot.get("api") else "",
        f"기준 {esc(sot['base'])}" if sot.get("base") else "") if x)
    body = (f"<h1>2 · 화면 · SOT 맵</h1><p class=\"meta\">{meta}</p>"
            + conclusion_html(sot.get("status", "wait"), sot.get("summary", ""), sot.get("conclusion", []))
            + (f'<div class="sum">{chips}</div>' if chips else "") + "".join(parts))
    (root / "02-screen.html").write_text(shell(task, "2 화면", body, css=("sot.css",), js=("sot.js",), wide=True))


# ---------------------------------------------------------------- 03 questions

def build_grill(root, task):
    grill = read_json(root / "data/grill.json", {"rounds": []})
    forms, concl, waiting, revised, decided = [], [], [], [], 0
    for r in grill["rounds"]:
        is_open = not all(q.get("decision") for q in r["questions"])
        is_revised = bool(r.get("revised")) and not is_open
        if is_open:
            waiting.append(r)
        elif is_revised:
            revised.append(r)
        if not is_open:
            decided += len(r["questions"])
            concl.extend(q["decision"] for q in r["questions"])
        cards = []
        for q in r["questions"]:
            a = q.get("answer") or {}
            options = q.get("options") or [{"value": "yes", "label": "추천대로"}, {"value": "no", "label": "다르게"}]
            options = options + [{"value": "unsure", "label": "더 설명해줘"}]
            rec = q.get("recommended", "yes")
            radios = "".join(
                f'<label class="{"rec" if o["value"] == rec else ""}"><input type="radio" '
                f'name="{r["id"]}-{q["id"]}" value="{esc(o["value"])}"{" checked" if a.get("choice") == o["value"] else ""}>'
                f'{o["label"]}</label>' for o in options)
            decision = ""
            if q.get("decision"):
                decision = (f'<div class="decision"><b>결정</b> {q["decision"]}'
                            f'<div class="applied">반영한 곳: {q.get("appliedTo", "")}</div></div>')
            cards.append(
                f'<div class="q" data-q="{q["id"]}"><b>{q["id"].upper()}. {q["title"]}</b>'
                f'<div class="said">{q["said"]}</div><div>{q["body"]}</div>'
                f'<div class="rec-line"><b>추천</b> {q["recommendation"]}</div><div class="opts">{radios}</div>'
                f'<textarea data-note placeholder="메모 (다르게 고르면 조건을 적어 주세요)">{esc(a.get("note", ""))}</textarea>'
                f'<textarea data-follow placeholder="되묻고 싶은 것">{esc(a.get("followUp", ""))}</textarea>{decision}</div>')
        if is_open:
            cls, badge, button = "open", '<span class="badge open">답을 기다려요</span>', "저장"
        elif is_revised:
            cls, badge, button = "revised", '<span class="badge revised">답이 바뀜 · 반영 전</span>', "고친 답 저장"
        else:
            cls, badge, button = "", '<span class="badge settled">결정됨 · 고칠 수 있어요</span>', "고친 답 저장"
        inner = "".join(cards) + f'<div class="savebar"><button type="submit">{button}</button></div>'
        if not is_open and not is_revised:
            inner = f"<details><summary>질문 {len(cards)}개 펼치기 · 답을 바꾸려면 펼쳐서 고치고 저장</summary>{inner}</details>"
        forms.append(f'<form class="round-form {cls}" data-round="{r["id"]}">'
                     f'<h2>{r["id"].upper()} · {r["askedAt"]} · {r["from"]}{badge}</h2>{inner}</form>')
    for r in waiting:
        concl.append(f"{r['id'].upper()}이 열려 있어요({r['from']}). 답을 기다려요.")
    for r in revised:
        concl.append(f"{r['id'].upper()}의 답이 바뀌었어요. 위 결정은 바뀌기 전 내용이라 Claude가 다시 반영해야 해요.")
    if not grill["rounds"]:
        status, summary, concl = "wait", "질문 없음", ["아직 질문이 없어요."]
    elif waiting or revised:
        status = "ask"
        summary = " · ".join([f"{r['id'].upper()} 답 대기" for r in waiting] + [f"{r['id'].upper()} 답 수정됨" for r in revised])
    else:
        status, summary = "done", f"남은 질문 0 · 결정 {decided}"
    body = ('<h1>3 · 질문</h1><p class="meta">질문과 답이 이 파일에 쌓여요. 결정된 라운드도 펼쳐서 답을 고칠 수 있어요.</p>'
            + conclusion_html(status, summary, concl) + "".join(reversed(forms))
            + '<p class="note">다음 단계는 위 결론만 읽어요. 아래 라운드는 사람이 보고 고치는 곳이에요.</p>')
    (root / "03-grill.html").write_text(shell(task, "3 질문", body))


# ---------------------------------------------------------------- index + nav

def stage_info(root):
    steps = []
    for n, (name, title) in enumerate(STAGES, 1):
        path = root / name
        if not path.exists():
            steps.append({"n": n, "file": name, "title": title, "status": "wait", "summary": "아직 없음", "body": ""})
            continue
        src = path.read_text()
        m = CONCLUSION.search(src)
        status, summary, body = (m.group(1), html.unescape(m.group(2)), m.group(3)) if m else ("wait", "결론 블록 없음", "")
        total = len(re.findall(r'data-check="', src))
        if total:
            checked = len(re.findall(r'data-check="[^"]+" checked', src))
            summary = f"{summary} · 체크 {checked}/{total}"
        steps.append({"n": n, "file": name, "title": title, "status": status, "summary": summary, "body": body})
    return steps


def nav_html(task, steps, current):
    now = next((s["n"] for s in steps if s["status"] in ("ask", "now")), None)
    reads = [f"{s['n']:02d} 결론" for s in steps if now and s["n"] < now] + ([f"{now:02d} 전체"] if now else [])
    links = "".join(
        f'<a class="step {s["status"]}{" on" if s["file"] == current else ""}" data-n="{s["n"]}" href="{s["file"]}" '
        f'title="{s["n"]} · {esc(s["title"])} — {esc(s["summary"])}"><b>{s["title"]}</b><span>{esc(s["summary"])}</span></a>'
        for s in steps)
    meta = " · ".join(x for x in (task.get("key"), task.get("type")) if x)
    return (
        "<!-- flow:nav -->"
        '<button class="navtoggle" id="navtoggle" title="목록 접기/펴기 ([ 키)" aria-label="목록 접기/펴기">☰</button>'
        f'<aside class="nav"><a class="home{" on" if current == "index.html" else ""}" href="index.html">{esc(task["title"])}</a>'
        f'<p class="nav-meta">{esc(meta)}</p><nav class="steps">{links}</nav>'
        '<div class="legend"><i class="l-done"></i>완료 <i class="l-now"></i>진행 중 <i class="l-ask"></i>질문 · 결정 대기 <i class="l-wait"></i>시작 전</div>'
        f'<div class="foot"><b>이어받을 때 읽는 것</b><br>{" → ".join(reads) if reads else "index 결론만"}</div></aside>'
        "<!-- /flow:nav -->"
    )


def build_index(root, task, steps):
    cards = "".join(
        f'<section class="stage-card {s["status"]}"><h2><a href="{s["file"]}">{s["n"]} · {s["title"]}</a>'
        f'<span class="st">{esc(s["summary"])}</span></h2><ul>{re.sub(r"^.*?<ul>|</ul>$", "", s["body"], flags=re.S)}</ul></section>'
        for s in steps)
    links = "".join(f'<li><a href="{esc(l["url"])}">{esc(l["label"])}</a></li>' for l in task.get("links", []))
    body = (f'<h1>{esc(task["title"])}</h1><p class="meta">{esc(" · ".join(x for x in (task.get("key"), task.get("type")) if x))}</p>'
            + (f'<ul class="links">{links}</ul>' if links else "")
            + '<p class="note">단계마다 결론만 모은 지도예요. 제목을 누르면 그 단계 문서로 가요.</p>' + cards)
    (root / "index.html").write_text(shell(task, "개요", body))


def write_nav(root, task):
    steps = stage_info(root)
    build_index(root, task, steps)
    for name in ["index.html"] + [s for s, _ in STAGES]:
        path = root / name
        if path.exists():
            src = path.read_text()
            if not NAV.search(src):
                sys.exit(f"{name}에 <!-- flow:nav --><!-- /flow:nav --> 자리가 없어요")
            path.write_text(NAV.sub(lambda _: nav_html(task, steps, name), src, count=1))


def build(root):
    task = read_json(root / "data/task.json")
    dest = root / "assets"
    dest.mkdir(exist_ok=True)
    for f in (SKILL / "assets").iterdir():
        shutil.copy(f, dest / f.name)
    if (root / "data/sot.json").exists():
        build_screen(root, task)
    build_grill(root, task)
    write_nav(root, task)


# ---------------------------------------------------------------- commands

def cmd_init(args):
    root = Path(args.dir)
    if (root / "data/task.json").exists():
        sys.exit(f"이미 있는 작업 폴더예요: {root}")
    (root / "data").mkdir(parents=True, exist_ok=True)
    task = {"id": root.name, "title": args.title, "key": args.key or "", "type": args.type, "links": []}
    write_json(root / "data/task.json", task)
    write_json(root / "data/grill.json", {"rounds": []})
    write_json(root / "data/inbox.json", {"entries": []})
    shutil.copy(SKILL / "templates/sot.template.json", root / "data/sot.json")
    for name in AUTHORED:
        src = (SKILL / "templates" / name.replace(".html", ".template.html")).read_text()
        (root / name).write_text(src.replace("{task-id}", esc(task["id"])).replace("{task-title}", esc(task["title"])))
    build(root)
    print(f"만들었어요: {root}")


def cmd_build(args):
    build(Path(args.dir))
    print("빌드했어요: 02-screen.html · 03-grill.html · index.html · 모든 페이지의 단계 목록")


def set_check(root, name, key, done):
    if name not in AUTHORED:
        sys.exit(f"체크 항목은 {', '.join(AUTHORED)}에만 있어요: {name}")
    path = root / name
    src = path.read_text()
    li = re.compile(r'<li data-key="' + re.escape(key) + r'"( class="done")?>')
    box = re.compile(r'<input type="checkbox" data-check="' + re.escape(key) + r'"( checked)?>')
    if not li.search(src) or not box.search(src):
        sys.exit(f"{name}에 항목 {key}가 없어요")
    src = li.sub(f'<li data-key="{key}"' + (' class="done"' if done else "") + ">", src, count=1)
    src = box.sub(f'<input type="checkbox" data-check="{key}"' + (" checked" if done else "") + ">", src, count=1)
    path.write_text(src)


def cmd_tick(args):
    root = Path(args.dir)
    set_check(root, args.file, args.key, not args.undo)
    write_nav(root, read_json(root / "data/task.json"))
    print(f"{args.file} {args.key}: {'체크 해제' if args.undo else '체크'}")


def cmd_apply(args):
    root = Path(args.dir)
    inbox = read_json(root / "data/inbox.json", {"entries": []})
    if not inbox["entries"]:
        print("반영할 입력이 없어요")
        return
    grill = read_json(root / "data/grill.json", {"rounds": []})
    rounds = {r["id"]: r for r in grill["rounds"]}
    todo = []
    for e in inbox["entries"]:
        if e["type"] == "check":
            set_check(root, e["file"], e["key"], bool(e["done"]))
            todo.append(f"{e['file']} {e['key']}: 사람이 {'체크' if e['done'] else '체크 해제'}함")
        elif e["type"] == "answer":
            r = rounds.get(e["round"])
            q = next((q for q in (r or {}).get("questions", []) if q["id"] == e["question"]), None)
            if q is None:
                todo.append(f"{e['round']}-{e['question']}: 없는 질문이라 건너뜀")
                continue
            old = q.get("answer") or {}
            new = {k: e.get(k, "") for k in ("choice", "note", "followUp")}
            if all(old.get(k, "") == new[k] for k in new):
                continue
            q["answer"] = new
            tag = f"{r['id'].upper()}-{q['id'].upper()}"
            if new["choice"] == "unsure":
                q.pop("decision", None)
                todo.append(f"{tag}: '더 설명해줘' — 빠진 설명을 붙여 다음 라운드에서 다시 물어요")
            elif q.get("decision"):
                r["revised"] = True
                todo.append(f"{tag}: 결정된 답이 바뀜 — 결정 문장과 반영한 곳을 다시 써요")
            else:
                todo.append(f"{tag}: 새 답 — 결정 문장을 쓰고 반영한 곳에 옮겨요")
            if new["followUp"]:
                todo.append(f"{tag}: 되물음 \"{new['followUp']}\" — 답해야 해요")
    write_json(root / "data/grill.json", grill)
    write_json(root / "data/inbox.json", {"entries": []})
    build(root)
    print("반영했어요. Claude가 할 일:")
    for t in todo:
        print(f"- {t}")


def cmd_check(args):
    root = Path(args.dir)
    problems = []
    task = read_json(root / "data/task.json")
    for name, _ in STAGES:
        path = root / name
        if not path.exists():
            problems.append(f"{name}이 없어요")
            continue
        src = path.read_text()
        m = CONCLUSION.search(src)
        if not m:
            problems.append(f"{name}: 결론 블록이 없어요")
        elif m.group(1) not in STATUSES:
            problems.append(f"{name}: 상태 '{m.group(1)}'는 {'/'.join(STATUSES)} 중 하나여야 해요")
        if not NAV.search(src):
            problems.append(f"{name}: 단계 목록 자리가 없어요")
    now = [s for s in stage_info(root) if s["status"] == "now"]
    if len(now) > 1:
        problems.append("진행 중(now) 단계가 둘 이상이에요: " + ", ".join(s["file"] for s in now))
    sot = read_json(root / "data/sot.json", {})
    pending = [m["title"] for s in sot.get("screens", []) for m in s["markers"] if m["kind"] == "pending"]
    if pending and sot.get("status") == "done":
        problems.append("02가 완료인데 확인 필요 행이 남았어요: " + ", ".join(pending))
    grill = read_json(root / "data/grill.json", {"rounds": []})
    for r in grill["rounds"]:
        for q in r["questions"]:
            tag = f"{r['id'].upper()}-{q['id'].upper()}"
            if (q.get("answer") or {}).get("choice") not in (None, "", "unsure") and not q.get("decision"):
                problems.append(f"{tag}: 답은 있는데 결정 문장이 없어요")
            if q.get("decision") and not q.get("appliedTo"):
                problems.append(f"{tag}: 결정을 어디에 반영했는지(appliedTo)가 없어요")
        if r.get("revised"):
            problems.append(f"{r['id'].upper()}: 바뀐 답을 아직 반영하지 않았어요 (반영 후 revised를 지워요)")
    if read_json(root / "data/inbox.json", {"entries": []})["entries"]:
        problems.append("inbox.json에 반영 안 된 입력이 있어요 — apply를 먼저 실행해요")
    if problems:
        print(f"{task['title']}: 문제 {len(problems)}건")
        for p in problems:
            print(f"- {p}")
        sys.exit(1)
    print(f"{task['title']}: 문제 없음")


def cmd_merge_xml(args):
    base = ET.parse(args.base)
    index = {el.get("id"): el for el in base.iter()}
    parents = {child: parent for parent in base.iter() for child in parent}
    for path in args.expanded:
        exp = ET.parse(path).getroot()
        target = index.get(exp.get("id"))
        if target is None:
            sys.exit(f"{path}: 바탕 XML에 노드 {exp.get('id')}가 없어요")
        exp.set("x", target.get("x", "0"))
        exp.set("y", target.get("y", "0"))
        if target is base.getroot():
            sys.exit("화면 프레임 자체는 합칠 수 없어요")
        parent = parents[target]
        parent[list(parent).index(target)] = exp
        index = {el.get("id"): el for el in base.iter()}
        parents = {child: parent for parent in base.iter() for child in parent}
    base.write(args.out, encoding="unicode")
    print(f"합쳤어요: {args.out}")


def main():
    ap = argparse.ArgumentParser(description="flow task folder tool")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("dir")
    p.add_argument("--title", required=True)
    p.add_argument("--key")
    p.add_argument("--type", default="기능 개발")
    p.set_defaults(fn=cmd_init)
    for name, fn in (("build", cmd_build), ("apply", cmd_apply), ("check", cmd_check)):
        p = sub.add_parser(name)
        p.add_argument("dir")
        p.set_defaults(fn=fn)
    p = sub.add_parser("tick")
    p.add_argument("dir")
    p.add_argument("file")
    p.add_argument("key")
    p.add_argument("--undo", action="store_true")
    p.set_defaults(fn=cmd_tick)
    p = sub.add_parser("merge-xml")
    p.add_argument("base")
    p.add_argument("expanded", nargs="+")
    p.add_argument("-o", "--out", required=True)
    p.set_defaults(fn=cmd_merge_xml)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
