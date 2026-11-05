"""Move documents written by earlier /flow versions to the current layout.

v1 (task folders): docs/<task-name>/ with 01-plan.html … 06-done.html and data/task.json,
    sot.json, grill.json, inbox.json. 01/04/05/06 held their content in the HTML itself.
v2 (local server): the current domain JSON plus docs/.flow/ (server.mjs + viewer), a "flow" script
    in package.json, and the server's port file in the git directory.
"""
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path

from model import ITEM_ID, git, read_json, write_json

VOID = {"br", "img", "input", "hr", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "param", "track"}
V1_PAGES = {"plan": "01-plan.html", "tasks": "04-tasks.html", "verify": "05-verify.html", "done": "06-done.html"}


# ---------------------------------------------------------------- detect

def detect(docs):
    docs = Path(docs)
    server, v1 = [], []
    if (docs / ".flow" / "server.mjs").exists():
        server.append(docs / ".flow")
    top = Path(git(docs, "rev-parse", "--show-toplevel") or docs.parent)
    pkg = top / "package.json"
    if pkg.exists():
        try:
            if ".flow/server.mjs" in json.loads(pkg.read_text()).get("scripts", {}).get("flow", ""):
                server.append(pkg)
        except ValueError:
            pass
    gitdir = git(docs, "rev-parse", "--absolute-git-dir")
    if gitdir and (Path(gitdir) / "flow-server.json").exists():
        server.append(Path(gitdir) / "flow-server.json")
    for p in sorted(docs.iterdir()) if docs.is_dir() else []:
        if p.is_dir() and not (p / "domain.json").exists() and (p / "data" / "task.json").exists():
            v1.append(p)
    return server, v1


SERVER_WHAT = {".flow": "서버 · 뷰어 사본", "package.json": '"flow" 스크립트', "flow-server.json": "서버 포트 기록"}


def plan_server(docs):
    docs = Path(docs)
    server, _ = detect(docs)
    lines = []
    for p in server:
        tracked = bool(git(docs, "ls-files", "--", str(p.resolve())))
        what = SERVER_WHAT.get(p.name, "")
        lines.append(f"- {p} ({what}{', git에 커밋됨 — 공유 저장소 변경' if tracked else ''})")
    return lines


def clean_server(docs):
    docs = Path(docs)
    lines = []
    server, _ = detect(docs)
    for p in server:
        if p.name == ".flow":
            shutil.rmtree(p)
            lines.append(f"지웠어요: {p} (서버 · 뷰어 사본)")
        elif p.name == "package.json":
            text = p.read_text()
            data = json.loads(text)
            data["scripts"].pop("flow", None)
            if not data["scripts"]:
                data.pop("scripts")
            indent = 2 if '\n  "' in text else 4
            p.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n")
            lines.append(f'{p}에서 "flow" 스크립트를 뺐어요 — 공유 저장소 변경이니 팀에 알려 주세요')
        else:
            p.unlink()
            lines.append(f"지웠어요: {p} (서버 포트 기록)")
    return lines


# ---------------------------------------------------------------- tiny HTML tree

class Node:
    def __init__(self, tag, attrs=None):
        self.tag, self.attrs, self.children = tag, dict(attrs or {}), []

    def classes(self):
        return (self.attrs.get("class") or "").split()

    def kids(self, tag=None):
        return [c for c in self.children if isinstance(c, Node) and (tag is None or c.tag == tag)]

    def find(self, pred):
        for c in self.children:
            if isinstance(c, Node):
                if pred(c):
                    return c
                hit = c.find(pred)
                if hit:
                    return hit
        return None


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(text):
    t = Tree()
    t.feed(text)
    t.close()
    return t.root


def outer(node):
    if isinstance(node, str):
        return node.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    attrs = "".join(f' {k}="{(v or "").replace(chr(34), "&quot;")}"' if v is not None else f" {k}" for k, v in node.attrs.items())
    if node.tag in VOID:
        return f"<{node.tag}{attrs}>"
    return f"<{node.tag}{attrs}>{inner(node)}</{node.tag}>"


def inner(node):
    return "".join(outer(c) for c in node.children).strip()


def text_of(node):
    if isinstance(node, str):
        return node
    return "".join(text_of(c) for c in node.children)


V1_DEFAULTS = {"아직 시작 전이에요.", '<p class="note">아직 없어요.</p>', "PR 생성",
               "2 · SOT 맵의 근거를 실제 코드 파일:줄로 바꿈", "남은 Computed · 계산 행을 서버 요청 목록으로 정리"}


def is_template(s):
    return bool(re.search(r"\{[^{}\s][^{}]*\}", s))


def untouched(s):
    return is_template(s) or plain_text(s) in {plain_text(d) for d in V1_DEFAULTS}


def plain_text(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


# ---------------------------------------------------------------- v1 pages

def check_item(li):
    label = li.kids("label")[0] if li.kids("label") else li
    span = label.find(lambda n: n.tag == "span") or label
    bs = span.kids("b")
    rest = "".join(text_of(c) for c in span.children if c not in bs).strip()
    title = inner(bs[0]) if len(bs) == 1 and not rest else inner(span)
    rows = []
    for sub in li.kids("ul"):
        for row in sub.kids("li"):
            lab = row.find(lambda n: n.tag == "span" and "label" in n.classes())
            if lab:
                name = text_of(lab).strip().rstrip(":").strip()
                body = "".join(outer(c) for c in row.children if c is not lab).strip()
                rows.append([name, body])
            else:
                rows.append(["메모", inner(row)])
    box = label.find(lambda n: n.tag == "input")
    done = "done" in li.classes() or (box is not None and "checked" in box.attrs)
    return {"key": li.attrs.get("data-key", ""), "title": title, "done": done, "rows": rows}


def page_stage(path):
    """A v1 01/04/05/06 page → stage dict, or None when it is still the template."""
    root = parse_html(path.read_text())
    main = root.find(lambda n: n.tag == "main") or root
    concl = main.find(lambda n: n.tag == "section" and "conclusion" in n.classes())
    status = (concl.attrs.get("data-status") if concl else None) or "wait"
    summary = (concl.attrs.get("data-summary") if concl else "") or ""
    items = [inner(li) for ul in (concl.kids("ul") if concl else []) for li in ul.kids("li")]
    sections, cur = [], {"title": "", "nodes": []}
    for c in main.children:
        if c is concl or (isinstance(c, Node) and (c.tag == "h1" or (c.tag == "p" and "meta" in c.classes()))):
            continue
        if isinstance(c, Node) and c.tag == "h2":
            if cur["nodes"] or cur["title"]:
                sections.append(cur)
            cur = {"title": text_of(c).strip(), "nodes": []}
            continue
        if isinstance(c, str) and not c.strip():
            continue
        cur["nodes"].append(c)
    if cur["nodes"] or cur["title"]:
        sections.append(cur)
    blocks = []
    for sec in sections:
        checks = [n for n in sec["nodes"] if isinstance(n, Node) and n.tag == "ul" and "check" in n.classes()]
        other = "".join(outer(n) for n in sec["nodes"] if n not in checks).strip()
        if checks:
            block = {"type": "checklist", "title": sec["title"], "items": [check_item(li) for ul in checks for li in ul.kids("li")]}
            m = re.search(r"Phase\s*(\d+)", sec["title"])
            if m:
                block["id"] = f"P{m.group(1)}"
            blocks.append(block)
            if other:
                blocks.append({"type": "text", "title": "", "html": other})
        elif other:
            blocks.append({"type": "text", "title": sec["title"], "html": other})
    texts = items + [b.get("html", "") for b in blocks if b["type"] == "text"]
    texts += [i["title"] for b in blocks for i in b.get("items", [])]
    done = any(i["done"] for b in blocks for i in b.get("items", []))
    if not done and all(untouched(t) for t in texts):
        return None
    return {"status": status if status in ("done", "now", "ask", "wait") else "wait",
            "summary": summary, "conclusion": items, "blocks": blocks}


def assign_ids(key, stage, taken, idmap):
    seq = 0
    for b in stage.get("blocks", []):
        if b.get("type") != "checklist":
            continue
        phase = (b.get("id") or "P0")[1:]
        for it in b["items"]:
            old = it.pop("key", "")
            up = old.upper()
            if key == "tasks":
                new = up if up and ITEM_ID.match(up) and up.startswith("P") else None
            elif key == "verify":
                new = f"B{re.sub(r'[^0-9]', '', up)}" if re.fullmatch(r"B\d+", up) else None
            else:
                new = up if re.fullmatch(r"D\d+", up) else None
            while not new or new in taken:
                seq += 1
                new = {"tasks": f"P{phase}-{seq}", "verify": f"V{seq}", "done": f"D{seq}"}[key]
            taken.add(new)
            it["id"] = new
            if not it["rows"]:
                del it["rows"]
            if old:
                idmap[(V1_PAGES[key], old)] = new


# ---------------------------------------------------------------- v1 → domain

def next_num(screens, letter):
    nums = [int(x["id"][1:]) for s in screens for x in s.get("markers" if letter == "S" else "offscreen", [])
            if re.fullmatch(rf"{letter}\d+", str(x.get("id", "")))]
    return max(nums, default=0) + 1


def convert_v1(docs, src, domain_id, title=None, keep=False):
    docs, src = Path(docs), Path(src)
    data = src / "data"
    old_task = read_json(data / "task.json")
    dom_dir = docs / domain_id
    report = []
    sot = read_json(data / "sot.json", {})
    if not (dom_dir / "domain.json").exists():
        if not title:
            raise SystemExit(f"새 도메인 {domain_id}를 만들려면 --title이 필요해요")
        first = next((s.get("figma", "") for s in sot.get("screens", [])), "")
        nodes = [s.get("figma", "").split()[0] for s in sot.get("screens", []) if s.get("figma")]
        (dom_dir / "tasks").mkdir(parents=True, exist_ok=True)
        (dom_dir / "images").mkdir(exist_ok=True)
        write_json(dom_dir / "domain.json", {"title": title, "kind": "screens", "figma": first, "nodes": nodes, "paths": [], "links": []})
        write_json(dom_dir / "screens.json", {"api": "", "base": "", "flows": [], "screens": []})
        report.append(f"도메인을 만들었어요: {dom_dir}")
    task_id = old_task.get("key") or src.name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", task_id):
        task_id = re.sub(r"[^A-Za-z0-9-]+", "-", task_id).strip("-") or src.name
    target = dom_dir / "tasks" / f"{task_id}.json"
    if target.exists():
        raise SystemExit(f"이미 있는 작업이에요: {target}")

    screens = read_json(dom_dir / "screens.json", {"api": "", "base": "", "flows": [], "screens": []})
    marker_map = {}
    if sot.get("screens") or sot.get("flows"):
        s_num, x_num = next_num(screens["screens"], "S"), next_num(screens["screens"], "X")
        taken = {s.get("id") for s in screens["screens"]}
        (dom_dir / "images").mkdir(exist_ok=True)
        n = 0
        for s in sot.get("screens", []):
            new = {k: v for k, v in s.items() if k not in ("markers", "offscreen")}
            sid = s.get("id") or re.sub(r"[^a-z0-9]+", "-", Path(s.get("image", "screen")).stem.lower()).strip("-") or "screen"
            while sid in taken:
                sid += "-v1"
            taken.add(sid)
            new["id"] = sid
            for field in ("image", "metadata"):
                if s.get(field) and (data / s[field]).exists():
                    dest = dom_dir / "images" / Path(s[field]).name
                    if dest.exists():
                        dest = dest.with_name(f"{task_id}-{dest.name}")
                    shutil.copy(data / s[field], dest)
                    new[field] = f"images/{dest.name}"
            new["markers"] = []
            for m in s.get("markers", []):
                n += 1
                mm = dict(m)
                mm["id"] = f"S{s_num}"
                marker_map[n] = mm["id"]
                s_num += 1
                new["markers"].append(mm)
            new["offscreen"] = []
            for o in s.get("offscreen", []):
                row = dict(zip(("state", "when", "shows"), o)) if isinstance(o, list) else dict(o)
                row["id"] = f"X{x_num}"
                x_num += 1
                new["offscreen"].append(row)
            screens["screens"].append(new)
        screens["flows"] = screens.get("flows", []) + sot.get("flows", [])
        for k in ("api", "base"):
            if sot.get(k) and not screens.get(k):
                screens[k] = sot[k]
        write_json(dom_dir / "screens.json", screens)
        if marker_map:
            report.append("SOT 번호가 바뀌었어요 (v1 번호 → ID): " + ", ".join(f"{a}→{b}" for a, b in marker_map.items()))

    stages, idmap, taken = {}, {}, set()
    for key in ("plan", "screen", "grill", "tasks", "verify", "done"):
        if key == "screen":
            if sot.get("screens") or sot.get("flows") or sot.get("status", "wait") != "wait":
                stages["screen"] = {"status": sot.get("status", "wait"), "summary": sot.get("summary", ""),
                                    "conclusion": sot.get("conclusion", [])}
            continue
        if key == "grill":
            grill = read_json(data / "grill.json", {"rounds": []})
            rounds = []
            for r in grill.get("rounds", []):
                rr = {k: v for k, v in r.items() if k not in ("revised",)}
                rr["id"] = r["id"].upper()
                rr["questions"] = [{**q, "id": q["id"].upper()} for q in r.get("questions", [])]
                rounds.append(rr)
            if rounds:
                stages["grill"] = {"rounds": rounds}
            continue
        page = src / V1_PAGES[key]
        if page.exists():
            st = page_stage(page)
            if st:
                assign_ids(key, st, taken, idmap)
                stages[key] = st
    inbox = read_json(data / "inbox.json", {"entries": []}).get("entries", [])
    for e in inbox:
        if e.get("type") == "answer" and "grill" in stages:
            r = next((x for x in stages["grill"]["rounds"] if x["id"] == str(e.get("round", "")).upper()), None)
            q = next((x for x in (r or {}).get("questions", []) if x["id"] == str(e.get("question", "")).upper()), None)
            if q:
                q["answer"] = {"choice": e.get("choice", ""), "note": e.get("note", ""), "followUp": e.get("followUp", ""), "by": "user"}
        elif e.get("type") == "check":
            new = idmap.get((e.get("file"), e.get("key")))
            for st in stages.values():
                for b in st.get("blocks", []):
                    for it in b.get("items", []):
                        if it.get("id") == new:
                            it["done"] = bool(e.get("done"))
                            it["by"] = "user"
    task = {"id": task_id, "title": old_task.get("title", task_id), "type": old_task.get("type", "기능 개발"),
            "branch": "", "links": old_task.get("links", []), "stages": stages}
    write_json(target, task)
    report.append(f"작업을 옮겼어요: {target} — 단계 {', '.join(stages) or '없음'}")
    texts = [f"{k} '{b.get('title') or '(제목 없음)'}'" for k, st in stages.items() for b in st.get("blocks", []) if b.get("type") == "text"]
    if texts:
        report.append("글 블록으로 옮긴 곳 — 읽고 표 · 인용 · 참조([[S5]])로 바꿀 것이 있으면 고쳐요: " + "; ".join(texts))
    pending = sum(1 for st in stages.values() for b in st.get("blocks", []) for it in b.get("items", []) if it.get("by") == "user")
    if pending or any(e.get("type") == "answer" for e in inbox):
        report.append("v1 inbox에 반영 안 된 답 · 체크가 있었어요 — flow.py changes로 처리해요")
    if keep:
        report.append(f"이전 폴더는 그대로 뒀어요: {src}")
    elif git(docs, "status", "--porcelain", "--", str(src.resolve())) or not git(docs, "ls-files", "--", str(src.resolve())):
        report.append(f"이전 폴더에 커밋 안 된 내용이 있어 지우지 않았어요: {src} — 확인한 뒤 직접 지워요")
    else:
        shutil.rmtree(src)
        report.append(f"이전 폴더를 지웠어요 (git 기록에 남아 있음): {src}")
    return report
