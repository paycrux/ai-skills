"""Render a docs folder's flow JSON into static, linked HTML pages."""
import html
import json
import posixpath
import re
from pathlib import Path

from model import (DEFAULT_OPTIONS, KIND, REF, STAGE_FILE, STAGE_KEYS, STAGE_TITLE, STAGES, STATE_LABEL, UNSURE,
                   domains_of, frame_boxes, git, grill_state, parse_ref, place, plain, read_json, stage_state,
                   task_files, task_items, task_state, walk_refs)

SKILL = Path(__file__).resolve().parent.parent
ASSETS = SKILL / "assets"
FONTS = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
GENERATOR = '<meta name="generator" content="flow">'
LEGACY_EXT = {".md", ".html"}


def esc(text):
    return html.escape(str(text if text is not None else ""), quote=True)


def copy_marks(text):
    return re.sub(r"“([^”]+)”", r'<span class="copy">\1</span>', text)


def is_generated(path):
    try:
        with open(path, encoding="utf-8") as f:
            return GENERATOR in f.read(600)
    except (OSError, UnicodeDecodeError):
        return False


# ---------------------------------------------------------------- site model

class Site:
    def __init__(self, docs):
        self.docs = Path(docs)
        self.domains = {}
        for d in domains_of(self.docs):
            info = read_json(d / "domain.json")
            screens = read_json(d / "screens.json", {"screens": []})
            tasks = {}
            for f in task_files(d):
                t = read_json(f)
                tasks[t["id"]] = t
            self.domains[d.name] = {"dir": d, "info": info, "screens": screens, "tasks": tasks,
                                    "items": {tid: task_items(t) for tid, t in tasks.items()}}
        root = self.docs / "index.html"
        self.root = "index.html" if not root.exists() or is_generated(root) else "flow-index.html"
        remote = git(self.docs, "remote", "get-url", "origin")
        top = git(self.docs, "rev-parse", "--show-toplevel")
        self.repo = re.sub(r"\.git$", "", remote.rstrip("/").split("/")[-1].split(":")[-1]) if remote else Path(top or self.docs.parent).name

    def domain_page(self, d):
        return f"{d}/index.html"

    def task_page(self, d, t, key=None):
        return f"{d}/{t}/{STAGE_FILE[key] if key else 'index.html'}"

    def sot(self, d, item):
        dom = self.domains.get(d)
        if not dom:
            return None
        for s in dom["screens"].get("screens", []):
            for m in s.get("markers", []):
                if m.get("id") == item:
                    return s, m, "marker"
            for o in s.get("offscreen", []):
                if o.get("id") == item:
                    return s, o, "offscreen"
        return None


class Ctx:
    """One page being rendered: where it is and which references it shows."""

    def __init__(self, site, path, domain=None, task=None):
        self.site, self.path, self.domain, self.task = site, path, domain, task
        self.refs = {}

    def href(self, target):
        base = posixpath.dirname(self.path) or "."
        anchor = ""
        if "#" in target:
            target, anchor = target.split("#", 1)
            anchor = "#" + anchor
        rel = posixpath.relpath(target, base) if target else posixpath.basename(self.path)
        return rel + anchor

    def resolve(self, raw):
        """→ (target path with anchor relative to docs, preview dict) or (None, None)."""
        site = self.site
        d, t, item = parse_ref(raw, self.domain, self.task)
        dom = site.domains.get(d)
        if not dom:
            return None, None
        if t is None:
            hit = site.sot(d, item) if item else None
            if not hit:
                return None, None
            s, node, kind = hit
            if kind == "marker":
                label, cls = KIND.get(node.get("kind"), ("?", "pend"))
                field = node.get("field") or ""
                body = f'<span class="k {cls}">{esc(label)}</span> ' + (f"{field} · " if field and field != "—" else "") + (node.get("rule") or "")
                prev = {"where": f"{d} · {s.get('title', '')}", "title": f"{node['id']} {node.get('title', '')}", "body": body}
            else:
                prev = {"where": f"{d} · {s.get('title', '')} · 화면 밖", "title": f"{node['id']} {node.get('state', '')}",
                        "body": f"{node.get('when', '')} → {node.get('shows', '')}"}
            return f"{site.domain_page(d)}#{item}", prev
        task = dom["tasks"].get(t)
        if not task:
            return None, None
        if item is None:
            return site.task_page(d, t), {"where": f"{d} · 작업", "title": f"{t} {task.get('title', '')}",
                                          "body": STATE_LABEL[task_state(task)]}
        found = dom["items"][t].get(item)
        if not found:
            return None, None
        key, node = found
        where = f"{t} · {STAGE_TITLE.get(key, key)}"
        if "questions" in node:
            prev = {"where": where, "title": f"{item} · {node.get('from', '')}",
                    "body": " · ".join(esc(plain(q.get("title", ""))) for q in node.get("questions", []))}
        elif "recommendation" in node or "said" in node:
            prev = {"where": where, "title": f"{item} {node.get('title', '')}", "body": node.get("decision") or "답을 기다려요"}
        elif "cells" in node:
            first = node["cells"][0] if node["cells"] else ""
            first = first.get("text", "") if isinstance(first, dict) else first
            prev = {"where": where + " · 케이스", "title": f"{item} {plain(first)}",
                    "body": " · ".join(ch.get("label", "") for ch in node.get("status", []))}
        elif node.get("type") == "cases":
            prev = {"where": where + " · 케이스", "title": f"{item} {node.get('title') or node.get('subtitle', '')}",
                    "body": "<br>".join(f"{r.get('id', '')} {plain((r['cells'][0].get('text', '') if isinstance(r['cells'][0], dict) else r['cells'][0]) if r.get('cells') else '')}"
                                        for r in node.get("rows", []))}
        elif "items" in node:
            prev = {"where": where, "title": node.get("title", ""),
                    "body": "<br>".join(f"{'✓' if i.get('done') else '○'} {i.get('title', '')}" for i in node["items"])}
        else:
            prev = {"where": where, "title": f"{item} {node.get('title', '')}",
                    "body": "<br>".join(f"{a}: {b}" for a, b in node.get("rows", []))}
        return f"{site.task_page(d, t, key)}#{item}", prev

    def rich(self, text):
        def link(m):
            raw = m.group(1)
            target, prev = self.resolve(raw)
            if not target:
                return f'<a class="ref broken" data-raw="{esc(raw)}" title="찾을 수 없는 참조">{esc(raw)}</a>'
            if raw not in self.refs:
                self.refs[raw] = {k: (v if k == "where" else flat_refs(v)) for k, v in prev.items()}
            return f'<a class="ref" data-raw="{esc(raw)}" href="{esc(self.href(target))}">{esc(raw)}</a>'
        return REF.sub(link, str(text if text is not None else ""))


def plain_refs(text):
    return REF.sub(lambda m: m.group(1), str(text if text is not None else ""))


def flat_refs(text):
    return REF.sub(lambda m: f'<code class="r">{esc(m.group(1))}</code>', str(text))


# ---------------------------------------------------------------- shared pieces

_ASSET_CACHE = {}


def asset(name):
    if name not in _ASSET_CACHE:
        _ASSET_CACHE[name] = (ASSETS / name).read_text()
    return _ASSET_CACHE[name]


def mock_theme(ctx):
    dom = ctx.site.domains.get(ctx.domain) if ctx.domain else None
    theme = (dom or {}).get("info", {}).get("mockTheme") or {}
    decls = "".join(f"--mock-{esc(k)}: {esc(v)};" for k, v in theme.items() if re.fullmatch(r"[a-z0-9-]+", k))
    return f"<style>:root{{{decls}}}</style>" if decls else ""


def shell(ctx, title, nav, body, wide=False, answers=None):
    data = json.dumps({"refs": ctx.refs, "answers": answers}, ensure_ascii=False).replace("</", "<\\/")
    return (
        "<!doctype html>\n<html lang=\"ko\"><head><meta charset=\"utf-8\">"
        f'<meta name="viewport" content="width=device-width,initial-scale=1">{GENERATOR}'
        f"<title>{esc(title)}</title><link rel=\"stylesheet\" href=\"{FONTS}\"><style>\n{asset('page.css')}</style>{mock_theme(ctx)}</head>\n<body>\n"
        '<script>try{if(localStorage.getItem("flow-nav-collapsed")==="1")document.body.classList.add("collapsed")}catch(e){}</script>\n'
        '<button class="navtoggle" id="navtoggle" title="목록 접기/펴기 ([ 키)" aria-label="목록 접기/펴기">☰</button>\n'
        f'<aside class="nav">{nav}</aside>\n<main class="page{" wide" if wide else ""}">\n{body}\n</main>\n'
        '<div class="savebar" id="savebar" hidden></div><div class="peek" id="peek" hidden></div><div class="toast" id="toast"></div>\n'
        f'<script type="application/json" id="flow-data">{data}</script>\n<script>\n{asset("page.js")}</script>\n</body></html>\n'
    )


LEGEND = ('<div class="legend"><span><i class="l-done"></i>완료</span><span><i class="l-now"></i>진행 중</span>'
          '<span><i class="l-ask"></i>질문 · 결정 대기</span><span><i class="l-wait"></i>시작 전</span></div>')


def conclusion(ctx, status, items):
    lis = "".join(f"<li>{ctx.rich(c)}</li>" for c in items or [])
    return f'<section class="conclusion" data-status="{esc(status)}"><h2>결론</h2><ul>{lis or "<li>아직 없어요.</li>"}</ul></section>'


def checklist(ctx, block):
    items = []
    for it in block.get("items", []):
        rows = "".join(f'<li><span class="label">{esc(a)}:</span> {ctx.rich(b)}</li>' for a, b in it.get("rows", []))
        srv = '<span class="k ans srv">사람이 체크 · 반영 전</span>' if it.get("by") == "user" else ""
        items.append(f'<li id="{esc(it["id"])}" class="{"done" if it.get("done") else ""}"><label>'
                     f'<input type="checkbox" data-check="{esc(it["id"])}"{" checked" if it.get("done") else ""}> '
                     f'<span><b>{ctx.rich(it.get("title", ""))}</b></span></label>{srv}{f"<ul>{rows}</ul>" if rows else ""}</li>')
    hid = f' id="{esc(block["id"])}"' if block.get("id") else ""
    empty = '<li class="note">아직 없어요.</li>'
    return f'<h2{hid}>{esc(block.get("title", ""))}</h2><ul class="check">{"".join(items) or empty}</ul>'


def quotes(ctx, items):
    groups = []
    for q in items:
        src = q.get("source", "")
        if not groups or groups[-1][0] != src:
            groups.append((src, []))
        groups[-1][1].append(q)
    out = "".join(f'<section class="qgroup">{f"<h4>{ctx.rich(src)}</h4>" if src else ""}<ul>'
                  + "".join(f"<li>{copy_marks(ctx.rich(q.get('text', '')))}</li>" for q in qs) + "</ul></section>"
                  for src, qs in groups)
    return f'<div class="quotes">{out}</div>'


def lines_html(text):
    return esc(text).replace("\n", "<br>")


def mock_text(text):
    parts = str(text or "").split("{copy}")
    return '<span data-slot></span>'.join(lines_html(x) for x in parts)


def mock_html(ctx, m):
    """One drawn UI piece: an app modal, toast or banner, or a Figma screenshot."""
    if "toast" in m:
        body = m["toast"]
        return f'<div class="mock mock-toast"><div class="tt{"" if body else " empty"}">{mock_text(body) if body else "문구 없음"}</div></div>'
    if "modal" in m:
        x = m["modal"]
        text = "".join(f'<div class="mm-{k}">{mock_text(x[k])}</div>' for k in ("title", "body") if x.get(k))
        btns = (f'<div class="mm-btn a">{esc(x["assistive"])}</div>' if x.get("assistive") else "") + f'<div class="mm-btn p">{esc(x.get("primary", "확인"))}</div>'
        return (f'<div class="mock"><div class="mm">{f"<div class=mm-text>{text}</div>" if text else ""}'
                f'<div class="mm-btns{" h" if x.get("assistive") else ""}">{btns}</div></div></div>')
    if "banner" in m:
        x = m["banner"]
        rows = "".join(f'<div class="bn-row"><span>{esc(a)}</span><span>{esc(b)}</span></div>' for a, b in x.get("rows", []))
        sub = f'<div class="bn-sub">{mock_text(x["sub"])}</div>' if x.get("sub") else ""
        return f'<div class="mock banner"><div class="bn">{mock_text(x.get("body", ""))}</div>{sub}{rows}</div>'
    if "shot" in m:
        x = m["shot"] if isinstance(m["shot"], dict) else {"src": m["shot"]}
        src = ctx.href(f"{ctx.domain}/{x['src']}") if ctx.domain else x["src"]
        return f'<figure class="shot-img{" dim" if x.get("dim") else ""}"><img src="{esc(src)}" alt="{esc(x.get("alt", ""))}"></figure>'
    return ""


def mocks_html(ctx, ms):
    if not ms:
        return ""
    return f'<div class="mocks">{"".join(mock_html(ctx, m) for m in ms)}</div>'


def case_cell(ctx, c, cls):
    if not isinstance(c, dict):
        return f'<td class="{cls}">{copy_marks(ctx.rich(c))}</td>'
    head = ""
    if c.get("ui") or c.get("figma"):
        fig = ' <span class="fig-tag">Figma</span>' if c.get("figma") else ""
        head = f'<div class="ui-kind">{ctx.rich(c.get("ui", ""))}{fig}</div>'
    enum = ""
    if c.get("enum"):
        enum = '<div class="enum"><span class="k out">enum</span>' + "".join(f"<code>{esc(e)}</code>" for e in c["enum"]) + "</div>"
    notes = c.get("note") or []
    notes = notes if isinstance(notes, list) else [notes]
    nt = "".join(f'<div class="nt">{copy_marks(ctx.rich(n))}</div>' for n in notes)
    text = copy_marks(ctx.rich(c.get("text", "")))
    return f'<td class="{cls}">{head}{text}{mocks_html(ctx, c.get("mocks"))}{nt}{enum}</td>'


def status_chips(ctx, chips):
    out = []
    for ch in chips or []:
        if ch.get("q"):
            out.append(f'<span class="k pend" data-status-for="{esc(ch["q"])}" data-label="{esc(ch.get("label", "답 대기"))}">{esc(ch.get("label", "답 대기"))}</span>')
        elif ch.get("state") == "done":
            out.append(f'<span class="dot">{esc(ch.get("label", "정리됨"))}</span>')
        else:
            out.append(f'<span class="k {esc(ch.get("state", "out"))}">{esc(ch.get("label", ""))}</span>')
    return "<br>".join(out)


def cases(ctx, b):
    cols = b.get("columns", [])
    head = "".join(f"<th>{esc(c)}</th>" for c in cols)
    rows = []
    for r in b.get("rows", []):
        cells = r.get("cells", [])
        tds = "".join(case_cell(ctx, c, "sit" if i == 0 else "") for i, c in enumerate(cells))
        ask = r.get("ask")
        preview = f'<div class="answer" data-preview-for="{esc(ask)}" hidden></div>' if ask else ""
        if preview:
            tds = tds[:-5] + preview + "</td>"
        if "status" in r:
            tds += f'<td class="st-cell">{status_chips(ctx, r["status"])}</td>'
        cls = " ".join(x for x in ("ask" if ask else "", "gone" if r.get("gone") else "") if x)
        rid = f' id="{esc(r["id"])}"' if r.get("id") else ""
        rows.append(f'<tr{rid}{f" class=" + chr(34) + cls + chr(34) if cls else ""}{f" data-row-for=" + chr(34) + esc(ask) + chr(34) if ask else ""}>{tds}</tr>')
    sub = f'<h3>{esc(b["subtitle"])}</h3>' if b.get("subtitle") else ""
    lead = f'<p class="lead">{copy_marks(ctx.rich(b["lead"]))}</p>' if b.get("lead") else ""
    return f'<div class="sec">{lead}{sub}<table class="cases"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def heading(b):
    hid = f' id="{esc(b["id"])}"' if b.get("id") else ""
    small = f'<small>{esc(b["sub"])}</small>' if b.get("sub") else ""
    return f'<h2{hid}>{esc(b.get("title", ""))}{small}</h2>'


def blocks(ctx, stage):
    out = []
    for b in stage.get("blocks", []):
        t = b.get("type")
        if t == "cases":
            out.append((heading(b) if b.get("title") else "") + cases(ctx, b))
        elif t == "checklist":
            out.append(checklist(ctx, b))
        elif t == "quote":
            out.append(f"<h2>{esc(b.get('title') or '인용')}</h2>{quotes(ctx, b.get('items', []))}")
        elif t == "table":
            head = "".join(f"<th>{esc(c)}</th>" for c in b.get("columns", []))
            rows = "".join("<tr>" + "".join(f"<td>{f'<b>{copy_marks(ctx.rich(c))}</b>' if i == 0 else copy_marks(ctx.rich(c))}</td>"
                                            for i, c in enumerate(r)) + "</tr>" for r in b.get("rows", []))
            out.append(f'<h2>{esc(b.get("title", ""))}</h2><table class="tbl"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>')
        else:
            cls = ' class="bridge"' if b.get("style") == "bridge" else ""
            out.append(f'{heading(b)}<div{cls}>{copy_marks(ctx.rich(b.get("html", "")))}</div>')
    return "".join(out)


def link_list(links):
    lis = "".join(f'<li><a href="{esc(l.get("url", ""))}" target="_blank" rel="noopener">{esc(l.get("label", ""))}</a></li>' for l in links or [])
    return f'<ul class="links">{lis}</ul>' if lis else ""


# ---------------------------------------------------------------- nav

def domain_state(dom):
    states = [task_state(t) for t in dom["tasks"].values()]
    active = len([x for x in states if x != "done"])
    if "ask" in states:
        return "ask"
    if "now" in states:
        return "now"
    if states and active == 0:
        return "done"
    return "now" if "done" in states else "wait"


def nav_steps(ctx, d, t, current):
    task = ctx.site.domains[d]["tasks"][t]
    steps = []
    for n, (k, title, fname) in enumerate(STAGES, 1):
        s = stage_state(task, k)
        if s["status"] == "skip":
            steps.append(f'<span class="step skip" data-n="{n}"><b>{esc(title)}</b><span>건너뜀</span></span>')
            continue
        on = " on" if current == k else ""
        summary = esc(plain_refs(s["summary"]))
        steps.append(f'<a class="step {s["status"]}{on}" data-n="{n}" href="{ctx.href(ctx.site.task_page(d, t, k))}" title="{summary}">'
                     f'<b>{esc(title)}</b><span>{summary}</span></a>')
    return f'<nav class="steps">{"".join(steps)}</nav>'


def nav_tree(ctx, d=None, t=None, current=None):
    site = ctx.site
    here = ctx.path
    doms = []
    for dd, dom in site.domains.items():
        mine = dd == d
        page = site.domain_page(dd)
        asks = [x for x in dom["tasks"].values() if task_state(x) == "ask"]
        cnt = f'<span class="cnt ask">질문 {len(asks)}</span>' if asks else f'<span class="cnt">{len(dom["tasks"]) or ""}</span>'
        rows = [f'<a class="tn done{" on" if here == page else ""}" href="{ctx.href(page)}">화면 · SOT 맵</a>']
        active, finished = [], []
        for tt, task in dom["tasks"].items():
            state = task_state(task)
            on = " on" if mine and tt == t and current is None else ""
            open_ = " open" if mine and tt == t else ""
            row = (f'<a class="tn {state}{on}{open_}" href="{ctx.href(site.task_page(dd, tt))}" title="{esc(tt)}">'
                   f'{esc(task.get("title") or tt)}</a>')
            if mine and tt == t:
                row += nav_steps(ctx, dd, tt, current)
            (finished if state == "done" else active).append((tt, row))
        rows += [r for _, r in active]
        if finished:
            fopen = " open" if mine and any(tt == t for tt, _ in finished) else ""
            rows.append(f'<details class="done-tasks"{fopen}><summary>끝난 작업 {len(finished)}</summary>'
                        + "".join(r for _, r in finished) + "</details>")
        doms.append(f'<details class="dom {domain_state(dom)}"{" open" if mine else ""}><summary>'
                    f'<a href="{ctx.href(page)}">{esc(dom["info"].get("title", dd))}</a>{cnt}</summary>'
                    f'<div class="dom-body">{"".join(rows)}</div></details>')
    foot = ""
    if d and t:
        links = site.domains[d]["tasks"][t].get("links", [])
        foot = "".join(f'<a href="{esc(l.get("url", ""))}" target="_blank" rel="noopener">{esc(l.get("label", ""))}</a>' for l in links)
    return (f'<a class="home" href="{ctx.href(site.root)}">{esc(site.repo)}</a><p class="nav-meta">flow 문서</p>'
            f'<a class="tn root{" on" if here == site.root else ""}" href="{ctx.href(site.root)}">전체 문서</a>'
            f'<div class="nav-group">도메인</div>{"".join(doms) or "<p class=note>아직 없어요</p>"}'
            f'{LEGEND}{f"<div class=foot>{foot}</div>" if foot else ""}')


# ---------------------------------------------------------------- pages

def legacy_files(site):
    out = []
    docs = site.docs

    def walk(folder, depth):
        for p in sorted(folder.iterdir()):
            if p.name.startswith("."):
                continue
            if p.is_dir():
                if depth == 0 and (p / "domain.json").exists():
                    continue
                if depth < 4:
                    walk(p, depth + 1)
            elif p.suffix in LEGACY_EXT and not is_generated(p):
                out.append(p.relative_to(docs).as_posix())

    walk(docs, 0)
    return out


def root_page(site):
    ctx = Ctx(site, site.root)
    rows = []
    for d, dom in site.domains.items():
        active = [(t, task) for t, task in dom["tasks"].items() if task_state(task) != "done"]
        lst = "".join(f'<div><a href="{ctx.href(site.task_page(d, t))}">{esc(t)} {esc(task.get("title", ""))}</a> '
                      f'<span class="st-dot {task_state(task)}">{STATE_LABEL[task_state(task)]}</span></div>' for t, task in active)
        rows.append(f'<div class="row"><h3><a href="{ctx.href(site.domain_page(d))}">{esc(dom["info"].get("title", d))}</a>'
                    f'<small>{esc(d)} · 작업 {len(dom["tasks"])}</small></h3><div>{lst or "<span class=note>진행 중인 작업 없음</span>"}</div></div>')
    legacy = legacy_files(site)
    leg = ""
    if legacy:
        leg = ("<h2>그 밖의 문서</h2><ul class=\"legacy-list\">"
               + "".join(f'<li><a href="{esc(ctx.href(p))}">{esc(p)}</a></li>' for p in legacy) + "</ul>")
    body = (f'<div class="head"><h1>{esc(site.repo)}</h1><p class="meta">도메인 {len(site.domains)} · 그 밖의 문서 {len(legacy)}</p></div>'
            f'<div class="cards">{"".join(rows) or "<p class=note>아직 flow 도메인이 없어요.</p>"}</div>{leg}')
    return shell(ctx, f"{site.repo} · flow", nav_tree(ctx), body)


def used_by(ctx, d):
    site = ctx.site
    used = {}
    for t, task in site.domains[d]["tasks"].items():
        for key, stage in (task.get("stages") or {}).items():
            def visit(raw, owner, t=t, key=key):
                rd, rt, item = parse_ref(raw, d, t)
                if rd != d or rt is not None or not item or not re.fullmatch(r"[SX]\d+", item):
                    return
                label = f"{t} {owner}" if owner else f"{t} {STAGE_TITLE.get(key, key)}"
                target = site.task_page(d, t, key) + (f"#{owner}" if owner else "")
                used.setdefault(item, {})[ctx.href(target)] = label
            walk_refs(stage, None, visit)
    return used


def used_html(links):
    if not links:
        return ""
    return '<div class="used">쓰는 곳 ' + " ".join(f'<a class="ref" href="{esc(h)}">{esc(l)}</a>' for h, l in links.items()) + "</div>"


def sot_map(ctx, d):
    dom = ctx.site.domains[d]
    sot = dom["screens"]
    comp = dom["info"].get("kind") == "components"
    field_head = "속성 · 토큰" if comp else "서버 필드"
    off_intro = "Figma에 그려지지 않았지만 코드가 다뤄야 하는 경우예요." if comp else "Figma 화면에는 없지만 데이터 때문에 생기는 경우예요."
    used = used_by(ctx, d)
    counts, parts = {}, []
    for f in sot.get("flows", []):
        rows = "".join(f"<tr><td>{ctx.rich(a)}</td><td>{ctx.rich(b)}</td></tr>" for a, b in f.get("rows", []))
        parts.append(f'<h2>흐름 · {esc(f.get("title", ""))}</h2><table><thead><tr><th>언제</th><th>결과</th></tr></thead><tbody>{rows}</tbody></table>')
    for s in sot.get("screens", []):
        frame = None
        meta = dom["dir"] / s.get("metadata", "")
        if s.get("metadata") and meta.exists():
            frame = frame_boxes(meta)
        pins, groups = [], []
        for m in s.get("markers", []):
            label, cls = KIND.get(m.get("kind"), ("?", "pend"))
            counts[label] = counts.get(label, 0) + 1
            xy = place(m, frame[0], frame[2]) if frame else None
            num = esc(m["id"][1:])
            if xy and xy[0] is not None and frame[0] and frame[1]:
                pins.append(f'<button class="pin k-{cls}" data-i="{esc(m["id"])}" data-x="{xy[0] / frame[0] * 100:.3f}" '
                            f'data-y="{xy[1] / frame[1] * 100:.3f}">{num}</button>')
            note = f'<div class="nt">{ctx.rich(m["note"])}</div>' if m.get("note") else ""
            row = (f'<tr id="{esc(m["id"])}" data-i="{esc(m["id"])}"{" class=ask" if m.get("kind") == "pending" else ""}>'
                   f'<td><span class="mk k-{cls}">{num}</span></td><td><b>{ctx.rich(m.get("title", ""))}</b><br><span class="k {cls}">{esc(label)}</span></td>'
                   f'<td>{ctx.rich(m.get("field") or "—")}</td><td>{ctx.rich(m.get("rule", ""))}{note}{used_html(used.get(m["id"]))}</td></tr>')
            sec = m.get("section") or "화면 요소"
            if not groups or groups[-1][0] != sec:
                groups.append((sec, []))
            groups[-1][1].append(row)
        tables = "".join(f'<h3>{esc(sec)}</h3><table><thead><tr><th></th><th>{"부분" if comp else "요소"}</th><th>{field_head}</th>'
                         f'<th>규칙 · 근거</th></tr></thead><tbody>{"".join(rows)}</tbody></table>' for sec, rows in groups)
        off = ""
        if s.get("offscreen"):
            orows = "".join(f'<tr id="{esc(o["id"])}"><td><span class="mk k-out">{esc(o["id"])}</span></td><td><b>{ctx.rich(o.get("state", ""))}</b>'
                            f'{used_html(used.get(o["id"]))}</td><td>{ctx.rich(o.get("when", ""))}</td><td>{ctx.rich(o.get("shows", ""))}</td></tr>'
                            for o in s["offscreen"])
            off = (f'<h3>화면 밖 상태</h3><p class="note">{esc(s.get("offscreenIntro") or off_intro)}</p><table><thead><tr><th></th>'
                   f'<th>상태</th><th>언제</th><th>보이는 것</th></tr></thead><tbody>{orows}</tbody></table>')
        variants = ""
        if s.get("variants"):
            vrows = "".join(f'<tr><td><b>{esc(v.get("axis", ""))}</b></td><td>{ctx.rich(v.get("values", ""))}</td><td>{ctx.rich(v.get("prop", ""))}</td>'
                            f'<td>{ctx.rich(v.get("note", ""))}</td></tr>' for v in s["variants"])
            variants = f'<h3>변형 축</h3><table class="tbl"><thead><tr><th>Figma 축</th><th>값</th><th>코드 속성</th><th>메모</th></tr></thead><tbody>{vrows}</tbody></table>'
        land = frame and (frame[0] > frame[1] or frame[0] > 700)
        if frame:
            shot = (f'<div class="shot"><div class="fig" data-w="{frame[0]:g}" data-h="{frame[1]:g}"><img src="{esc(s.get("image", ""))}" '
                    f'alt="{esc(s.get("title", ""))} Figma 화면">{"".join(pins)}</div></div>')
        else:
            shot = f'<div class="shot"><p class="note">구조 정보({esc(s.get("metadata", ""))})를 읽지 못했어요.</p></div>'
        parts.append(f'<h2 class="screen" id="screen-{esc(s.get("id", ""))}">{"컴포넌트" if comp else "화면"} · {esc(s.get("title", ""))}</h2>'
                     f'<p class="meta">Figma <code>{esc(s.get("figma", ""))}</code></p><div class="cols{" landscape" if land else ""}">{shot}<div>{variants}{tables}{off}</div></div>')
    chips = "".join(f"<span>{esc(k)} {v}</span>" for k, v in counts.items())
    meta = " · ".join(x for x in (f"API <code>{esc(sot['api'])}</code>" if sot.get("api") else "",
                                  f"기준 {esc(sot['base'])}" if sot.get("base") else "") if x)
    return f'{f"<p class=meta>{meta}</p>" if meta else ""}{f"<div class=sum>{chips}</div>" if chips else ""}{"".join(parts)}' or '<p class="note">아직 SOT 맵이 없어요.</p>'


def domain_page(site, d):
    dom = site.domains[d]
    ctx = Ctx(site, site.domain_page(d), d)
    info = dom["info"]
    tasks = "".join(f'<div class="row"><h3><a href="{ctx.href(site.task_page(d, t))}">{esc(t)}</a><small>{esc(task.get("type", ""))}</small></h3>'
                    f'<div>{esc(task.get("title", ""))} <span class="st-dot {task_state(task)}">{STATE_LABEL[task_state(task)]}</span></div></div>'
                    for t, task in dom["tasks"].items())
    sot = sot_map(ctx, d)
    figma = f' · Figma <code>{esc(info["figma"])}</code>' if info.get("figma") else ""
    empty = '<p class="note">아직 없어요.</p>'
    body = (f'<div class="head"><h1>{esc(info.get("title", d))}</h1><p class="meta">도메인 <code>{esc(d)}</code>{figma}</p></div>'
            f'{link_list(info.get("links"))}<h2>작업</h2><div class="cards">{tasks or empty}</div>{sot}')
    return shell(ctx, f"{info.get('title', d)} · flow", nav_tree(ctx, d), body, wide=True)


def answers_data(site, d, t):
    task = site.domains[d]["tasks"][t]
    questions, checks = {}, {}
    for r in ((task.get("stages") or {}).get("grill") or {}).get("rounds", []):
        for q in r.get("questions", []):
            a = q.get("answer") or {}
            questions[f"{r['id']}-{q['id']}"] = {
                "title": plain(q.get("title", "")), "options": q.get("options") or [],
                "answer": {k: a.get(k, "") for k in ("choice", "note", "followUp", "copy")},
                "decided": bool(q.get("decision")), "byUser": a.get("by") == "user"}
    for key, st in (task.get("stages") or {}).items():
        if key == "grill":
            continue
        for b in st.get("blocks", []):
            if b.get("type") == "checklist":
                for it in b.get("items", []):
                    checks[it["id"]] = {"title": plain(it.get("title", "")), "done": bool(it.get("done"))}
    return {"task": f"{d}/{t}", "title": task.get("title", t), "pulledAt": task.get("pulledAt", 0),
            "questions": questions, "checks": checks}


def task_index(site, d, t):
    dom = site.domains[d]
    task = dom["tasks"][t]
    ctx = Ctx(site, site.task_page(d, t), d, t)
    cards, skipped = [], []
    for n, (k, title, fname) in enumerate(STAGES, 1):
        s = stage_state(task, k)
        if s["status"] == "skip":
            skipped.append(f"{n} {title}")
            continue
        st = task["stages"][k]
        items = grill_conclusion(st, s) if k == "grill" else st.get("conclusion") or []
        lis = "".join(f"<li>{ctx.rich(c)}</li>" for c in items) or "<li>아직 없어요.</li>"
        cards.append(f'<section class="stage-card {s["status"]}"><h2><a href="{fname}"><span class="n">{n}</span>{esc(title)}</a>'
                     f'<span class="st">{esc(plain_refs(s["summary"]))}</span></h2><ul>{lis}</ul></section>')
    meta = " · ".join(x for x in (esc(dom["info"].get("title", d)), esc(t), esc(task.get("type", "")),
                                  f"<code>{esc(task['branch'])}</code>" if task.get("branch") else "") if x)
    note = f'<p class="note">건너뛴 단계: {esc(", ".join(skipped))}. 필요해지면 그때 만들어요.</p>' if skipped else ""
    body = (f'<div class="head"><h1>{esc(task.get("title", t))}</h1><p class="meta">{meta}</p></div>{link_list(task.get("links"))}'
            f'{"".join(cards)}{note}')
    return shell(ctx, f"{t} {task.get('title', '')} · flow", nav_tree(ctx, d, t), body)


def grill_conclusion(stage, s):
    out = []
    for r in stage.get("rounds", []):
        if r["id"] not in s["open"]:
            out += [q["decision"] for q in r.get("questions", []) if q.get("decision")]
    out += [f"{i}이 열려 있어요. 답을 기다려요." for i in s["open"]]
    out += [f"{i}의 답이 바뀌었어요. 결정은 바뀌기 전 내용이라 Claude가 다시 반영해야 해요." for i in s["revised"]]
    return out or ["아직 질문이 없어요."]


def grill_body(ctx, stage, s):
    forms = []
    for r in reversed(stage.get("rounds", [])):
        is_open, revised = r["id"] in s["open"], r["id"] in s["revised"]
        cards = []
        for q in r.get("questions", []):
            tag = f"{r['id']}-{q['id']}"
            a = q.get("answer") or {}
            opts = (q.get("options") or DEFAULT_OPTIONS) + [UNSURE]
            rec = q.get("recommended", "yes")
            radios = "".join(f'<label class="{"rec" if o["value"] == rec else ""}"><input type="radio" name="{esc(tag)}" value="{esc(o["value"])}"'
                             f'{" checked" if a.get("choice") == o["value"] else ""}>{esc(o["label"])}</label>' for o in opts)
            if a.get("by") == "user":
                badge = '<span class="k ans">답 받음 · 반영 전</span>'
            elif q.get("decision"):
                badge = '<span class="k done">결정됨</span>'
            else:
                badge = '<span class="k pend">답 대기</span>'
            ctxl = "".join(f'<li><b>{esc(k)}</b><span>{copy_marks(ctx.rich(v))}</span></li>' for k, v in q.get("context", []))
            ctxl = f'<ul class="q-ctx">{ctxl}</ul>' if ctxl else ""
            said = f'<div class="said">{ctx.rich(q["said"])}</div>' if q.get("said") else ""
            body = f'<div>{ctx.rich(q["body"])}</div>' if q.get("body") else ""
            cp = q.get("copy")
            copy_fld = (f'<label class="fld"><span>{esc(cp.get("label", "문구"))} · 줄바꿈 그대로</span><textarea data-f="copy" '
                        f'placeholder="{esc(cp.get("placeholder", "화면에 보일 문구 그대로"))}">{esc(a.get("copy", ""))}</textarea></label>') if cp else ""
            tpls = "".join(f'<template data-preview="{esc(k)}">{mocks_html(ctx, v if isinstance(v, list) else [v])}</template>'
                           for k, v in (q.get("preview") or {}).items())
            live = f'<div class="live" data-live>{tpls}</div>' if tpls else ""
            decision = (f'<div class="decision"><b>결정</b>{ctx.rich(q["decision"])}<div class="applied">반영한 곳: {ctx.rich(q.get("appliedTo", ""))}</div></div>'
                        if q.get("decision") else "")
            cls = "q open" if not q.get("decision") and a.get("by") != "user" else "q"
            cards.append(f'<div class="{cls}" id="{esc(tag)}" data-tag="{esc(tag)}"><div class="q-head"><b>{esc(tag)}. {ctx.rich(q.get("title", ""))}</b>{badge}</div>'
                         f'{ctxl}{said}{body}'
                         f'<div class="rec-line"><b>추천</b>{ctx.rich(q.get("recommendation", ""))}</div>'
                         f'<div class="q-grid{" has-live" if live else ""}"><div><div class="opts">{radios}</div>{copy_fld}'
                         f'<label class="fld"><span>메모</span><textarea data-f="note" placeholder="다르게 고르면 조건을 적어 주세요">{esc(a.get("note", ""))}</textarea></label>'
                         f'<label class="fld"><span>되묻기</span><textarea data-f="followUp" placeholder="되묻고 싶은 것">{esc(a.get("followUp", ""))}</textarea></label></div>{live}</div>'
                         f'{decision}</div>')
        if is_open:
            rb, inner = '<span class="k pend">답을 기다려요</span>', "".join(cards)
        elif revised:
            rb, inner = '<span class="k ans">답이 바뀜 · 반영 전</span>', "".join(cards)
        else:
            rb = '<span class="k done">결정됨</span>'
            inner = f'<details><summary>질문 {len(cards)}개 펼치기 · 답을 바꾸려면 펼쳐서 고쳐 주세요</summary>{"".join(cards)}</details>'
        forms.append(f'<div class="round" id="{esc(r["id"])}"><h2>{esc(r["id"])} · {esc(r.get("askedAt", ""))} · {ctx.rich(r.get("from", ""))}{rb}</h2>{inner}</div>')
    top = blocks(ctx, stage)
    qhead = '<h2 class="qs-head">질문<small>고르거나 적으면 위 표의 상태가 바로 바뀌어요</small></h2>' if top and forms else ""
    return conclusion(ctx, s["status"], grill_conclusion(stage, s)) + top + qhead + "".join(forms)


def screen_refs(ctx, task):
    seen = set()

    def visit(raw, owner):
        rd, rt, item = parse_ref(raw, ctx.domain, task["id"])
        if rd == ctx.domain and rt is None and item and re.fullmatch(r"[SX]\d+", item):
            seen.add(item)

    walk_refs(task.get("stages") or {}, None, visit)
    full = f'<a href="{ctx.href(ctx.site.domain_page(ctx.domain))}">도메인 SOT 맵 전체</a>'
    if not seen:
        return f"<h2>SOT 맵</h2><p>{full}</p>"
    ids = sorted(seen, key=lambda i: (i[0], int(i[1:])))
    return f'<h2>이 작업이 쓰는 행</h2><p>{" ".join(ctx.rich(f"[[{i}]]") for i in ids)} · {full}</p>'


def stage_page(site, d, t, key, n):
    dom = site.domains[d]
    task = dom["tasks"][t]
    ctx = Ctx(site, site.task_page(d, t, key), d, t)
    stage = task["stages"][key]
    s = stage_state(task, key)
    if key == "grill":
        body = grill_body(ctx, stage, s)
    else:
        body = conclusion(ctx, s["status"], stage.get("conclusion")) + blocks(ctx, stage)
        if key == "screen":
            body += screen_refs(ctx, task)
    head = (f'<div class="head"><h1><span class="n {s["status"]}">{n}</span>{esc(STAGE_TITLE[key])}</h1>'
            f'<p class="meta">{esc(task.get("title", t))} · {esc(t)} · {esc(plain_refs(s["summary"]))}</p></div>')
    return shell(ctx, f"{n} {STAGE_TITLE[key]} · {task.get('title', t)}", nav_tree(ctx, d, t, key), head + body,
                 answers=answers_data(site, d, t))


# ---------------------------------------------------------------- build

def render_all(docs):
    """→ {path relative to docs: html} for every page the JSON defines."""
    site = Site(docs)
    pages = {site.root: root_page(site)}
    for d, dom in site.domains.items():
        pages[site.domain_page(d)] = domain_page(site, d)
        for t, task in dom["tasks"].items():
            pages[site.task_page(d, t)] = task_index(site, d, t)
            for n, k in enumerate(STAGE_KEYS, 1):
                if k in (task.get("stages") or {}):
                    pages[site.task_page(d, t, k)] = stage_page(site, d, t, k, n)
    return site, pages


def orphans(site, pages):
    """Generated pages on disk that the JSON no longer defines."""
    out = []
    for d, dom in site.domains.items():
        for sub in sorted(p for p in dom["dir"].iterdir() if p.is_dir() and p.name not in ("tasks", "images")):
            for f in sorted(sub.glob("*.html")):
                rel = f.relative_to(site.docs).as_posix()
                if rel not in pages and is_generated(f):
                    out.append(rel)
    other = "flow-index.html" if site.root == "index.html" else "index.html"
    if (site.docs / other).exists() and is_generated(site.docs / other):
        out.append(other)
    return out


def stale(docs):
    site, pages = render_all(docs)
    out = []
    for rel, text in pages.items():
        p = site.docs / rel
        if not p.exists():
            out.append(f"{rel} 없음")
        elif p.read_text() != text:
            out.append(f"{rel} 원본과 다름")
    out += [f"{rel} 원본에 없는 페이지" for rel in orphans(site, pages)]
    return out


def build(docs):
    site, pages = render_all(docs)
    written = 0
    for rel, text in pages.items():
        p = site.docs / rel
        if p.exists() and p.read_text() == text:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        written += 1
    removed = orphans(site, pages)
    for rel in removed:
        p = site.docs / rel
        p.unlink()
        if p.parent != site.docs and not any(p.parent.iterdir()):
            p.parent.rmdir()
    return site, len(pages), written, removed
