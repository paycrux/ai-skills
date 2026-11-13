"""Render a docs folder's flow JSON into static, linked HTML pages."""
import html
import json
import posixpath
import re
from pathlib import Path

import feature as feat
import workflow
from model import (CORE_PAGES, DEFAULT_OPTIONS, ITEM_ID, KIND, PAGES, REASON_BY, REF, STAGE_TITLE, STATE_LABEL, UNSURE, domains_of,
                   frame_boxes, git, grill_state, page_file, page_state, parse_ref, place, plain, read_json, stage_state,
                   task_files, task_items, task_pages, task_state, unconfirmed, walk_refs)

SKILL = Path(__file__).resolve().parent.parent
ASSETS = SKILL / "assets"
FONTS = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
MARKED = "https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"
GENERATOR = '<meta name="generator" content="flow">'
LEGACY_EXT = {".md", ".html"}
AUDIENCE = {"plan": "기획", "backend": "백엔드"}
CONFIG = "flow.config.json"
HIDE_PAGES = {page for page, _, _, _ in CORE_PAGES}
HIDE_FIELDS = ("said", "context", "body", "preview", "note", "followUp")


def load_config(docs):
    """<docs>/flow.config.json → (config, problems). Pages stay renderable when it is broken."""
    path = Path(docs) / CONFIG
    if not path.exists():
        return {"style": "", "hide": set()}, []
    problems = []
    try:
        raw = json.loads(path.read_text())
    except ValueError as e:
        return {"style": "", "hide": set()}, [f"{CONFIG}: JSON을 읽지 못했어요 ({e})"]
    style = ""
    if raw.get("style"):
        css = Path(docs) / raw["style"]
        if css.is_file():
            style = css.read_text()
        else:
            problems.append(f"{CONFIG}: style 파일이 없어요 ({raw['style']})")
    hide = set()
    for h in raw.get("hide") or []:
        kind, _, name = str(h).partition(":")
        ok = ((kind == "page" and name in HIDE_PAGES) or (kind == "field" and name in HIDE_FIELDS)
              or (kind == "block" and name))
        if ok:
            hide.add(h)
        else:
            problems.append(f"{CONFIG}: hide '{h}' — page:<{'|'.join(sorted(HIDE_PAGES))}>, "
                            f"field:<{'|'.join(HIDE_FIELDS)}>, block:<type 또는 제목> 중 하나")
    unknown = sorted(set(raw) - {"style", "hide", "workflow"})
    if unknown:
        problems.append(f"{CONFIG}: 모르는 키 {', '.join(unknown)} — style · hide · workflow만 읽어요")
    return {"style": style, "hide": hide}, problems


def esc(text):
    return html.escape(str(text if text is not None else ""), quote=True)


# Text fields accept a little inline HTML (references/documents.md). JSON text can come from a PRD, Jira or a
# teammate's commit, so only these tags survive, and only without attributes; every other "<" is shown as text.
SAFE_TAGS = ("code|b|strong|em|i|u|s|mark|small|sub|sup|kbd|br|p|ul|ol|li|pre|blockquote|hr|h4|h5|"
             "table|thead|tbody|tr|th|td")
_SAFE_TAG = re.compile(rf"&lt;(/?)({SAFE_TAGS})\s*(/?)&gt;", re.I)
_OWN_TAG = re.compile(r'&lt;(span class=&quot;k [a-z-]+&quot;|/span|code class=&quot;r&quot;)&gt;')
_ENTITY = re.compile(r"&amp;(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")


def safe_html(text):
    out = html.escape(str(text if text is not None else ""), quote=True)
    out = _ENTITY.sub(r"&\1;", out)
    out = _SAFE_TAG.sub(lambda m: f"<{m.group(1)}{m.group(2).lower()}{m.group(3)}>", out)
    return _OWN_TAG.sub(lambda m: "<" + m.group(1).replace("&quot;", '"') + ">", out)


def safe_url(url):
    """A link from JSON: web, mail and file links only — a javascript: or data: URL becomes inert."""
    u = str(url or "").strip()
    scheme = re.match(r"([a-zA-Z][a-zA-Z0-9+.-]*):", u)
    return u if not scheme or scheme.group(1).lower() in ("http", "https", "mailto", "file") else "#"


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
        self.workflow = workflow.use(self.docs)
        self.domains = {}
        for d in domains_of(self.docs):
            info = read_json(d / "domain.json")
            screens = read_json(d / "screens.json", {"screens": []})
            tasks, mtimes = {}, {}
            for f in task_files(d):
                t = read_json(f)
                tasks[t["id"]] = t
                mtimes[t["id"]] = f.stat().st_mtime
            self.domains[d.name] = {"dir": d, "info": info, "screens": screens, "tasks": tasks, "mtimes": mtimes,
                                    "items": {tid: task_items(t) for tid, t in tasks.items()},
                                    "sot_ids": {tid: task_sot_ids(d.name, t) for tid, t in tasks.items()
                                                if "screen" in (t.get("stages") or {})}}
        self.features = {}
        for fd in feat.feature_dirs(self.docs):
            f = read_json(fd / "feature.json")
            f["id"] = fd.name
            self.features[fd.name] = f
        self._progress = {}
        self.config, _ = load_config(self.docs)
        root = self.docs / "index.html"
        self.root = "index.html" if not root.exists() or is_generated(root) else "flow-index.html"
        remote = git(self.docs, "remote", "get-url", "origin")
        top = git(self.docs, "rev-parse", "--show-toplevel")
        self.repo = re.sub(r"\.git$", "", remote.rstrip("/").split("/")[-1].split(":")[-1]) if remote else Path(top or self.docs.parent).name

    def hidden(self, kind, name):
        if f"{kind}:{name}" in self.config["hide"]:
            return True
        return False

    def domain_page(self, d):
        return f"{d}/index.html"

    def feature_page(self, fid):
        return f"{feat.FEATURES}/{fid}/index.html"

    def progress(self, fid):
        """Row key → progress, read once per build from each row's task."""
        if fid not in self._progress:
            f = self.features[fid]
            self._progress[fid] = {feat.row_key(r): feat.row_progress(self.docs, r) for r in f.get("rows", [])}
        return self._progress[fid]

    def feature_state(self, fid):
        states = [p["task"] and task_state(p["task"]) or ("ask" if p["state"] == "legacy" else "wait")
                  for p in self.progress(fid).values()]
        if not states:
            return "wait"
        for s in ("ask", "now"):
            if s in states:
                return s
        return "done" if all(x == "done" for x in states) else ("now" if "done" in states else "wait")

    def task_page(self, d, t, key=None):
        return f"{d}/{t}/{page_file(key) if key else 'index.html'}"

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
            if d == self.domain and item in dom["sot_ids"].get(self.task, ()):
                return f"{site.task_page(d, self.task, 'screen')}#{item}", prev
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

    def frame(self, target):
        return f'src="{esc(self.href(target))}"'

    def rich(self, text):
        def link(m):
            raw = m.group(1)
            target, prev = self.resolve(raw)
            if not target:
                return f'<a class="ref broken" data-raw="{esc(raw)}" title="찾을 수 없는 참조">{esc(raw)}</a>'
            if raw not in self.refs:
                self.refs[raw] = {k: (v if k == "where" else flat_refs(safe_html(v))) for k, v in prev.items()}
            return f'<a class="ref" data-raw="{esc(raw)}" href="{esc(self.href(target))}">{esc(raw)}</a>'
        return REF.sub(link, safe_html(text))


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


def user_style(ctx):
    out = ""
    for attr, css in (("data-flow-config", ctx.site.config["style"]), ("data-flow-personal", ctx.site.workflow["style"])):
        if css:
            css = css.replace("</", "<\\/")
            out += f"<style {attr}>\n{css}</style>"
    return out


def shell(ctx, title, nav, body, wide=False, answers=None, shared=None):
    texts = {who: x["md"] for who, x in (shared or {}).items()}
    data = json.dumps({"refs": ctx.refs, "answers": answers, "share": texts}, ensure_ascii=False).replace("</", "<\\/")
    return (
        "<!doctype html>\n<html lang=\"ko\"><head><meta charset=\"utf-8\">"
        f'<meta name="viewport" content="width=device-width,initial-scale=1">{GENERATOR}'
        f"<title>{esc(title)}</title><link rel=\"stylesheet\" href=\"{FONTS}\"><style>\n{asset('page.css')}</style>{mock_theme(ctx)}{user_style(ctx)}</head>\n<body>\n"
        '<script>try{if(localStorage.getItem("flow-nav-collapsed")==="1")document.body.classList.add("collapsed")}catch(e){}</script>\n'
        '<button class="navtoggle" id="navtoggle" title="목록 접기/펴기 ([ 키)" aria-label="목록 접기/펴기">☰</button>\n'
        f'<aside class="nav">{nav}</aside>\n<main class="page{" wide" if wide else ""}">\n{body}\n</main>\n'
        '<div class="savebar" id="savebar" hidden></div><div class="peek" id="peek" hidden></div><div class="toast" id="toast"></div>\n'
        f'<script type="application/json" id="flow-data">{data}</script>\n<script>\n{asset("page.js")}</script>\n</body></html>\n'
    )


LEGEND = ('<div class="legend"><span><i class="l-done"></i>완료</span><span><i class="l-now"></i>진행 중</span>'
          '<span><i class="l-ask"></i>질문 · 결정 대기</span><span><i class="l-wait"></i>시작 전</span></div>')


def export_menu(ctx, d, t, shared):
    if not shared:
        return ""
    rows = []
    for who, label, word in (("plan", "기획 · 디자인", "질문"), ("backend", "백엔드", "요청")):
        n = shared[who]["n"]
        state = f"{word} {n}건" if n else "확정본"
        rows.append(f'<div class="ex-row"><b>{label}</b><span>{state}</span>'
                    f'<button class="ex-btn" type="button" data-share="{who}">텍스트 복사</button></div>')
    return ('<details class="export"><summary>내보내기</summary><div class="ex-panel">'
            '<p class="note">이 작업을 기획 · 백엔드에 보낼 사본이에요. 받는 사람과 형식을 골라 주세요.</p>'
            f'{"".join(rows)}<p class="note">텍스트는 슬랙 본문이나 지라 댓글에 붙여 넣는 용도예요. '
            '그림이 든 HTML 파일이 필요하면 Claude에게 “기획 공유본 HTML 만들어줘”라고 하면 돼요 (<code>flow.py export</code>).</p></div></details>')


def conclusion(ctx, status, items=None, lis=None):
    lis = lis if lis is not None else "".join(f"<li>{ctx.rich(c)}</li>" for c in items or [])
    return f'<section class="conclusion" data-status="{esc(status)}"><h2>결론</h2><ul>{lis or "<li>아직 없어요.</li>"}</ul></section>'


def checklist(ctx, block):
    items = []
    for it in block.get("items", []):
        rows = "".join(f'<li><span class="label">{esc(a)}:</span> {ctx.rich(b)}</li>' for a, b in it.get("rows", []))
        srv = '<span class="k ans srv">사람이 체크 · 반영 전</span>' if it.get("by") == "user" else ""
        if it.get("by") == "inferred":
            srv += '<span class="k pend">추정 · 사람 확인 전</span>'
        if it.get("unknown"):
            srv += f'<span class="k out">모름 · {esc(it["unknown"])}</span>'
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
        src = ctx.href(f"{ctx.domain}/{x['src']}") if ctx.domain else safe_url(x["src"])
        cls = "shot-img" + (" dim" if x.get("dim") else "") + (" wide" if x.get("wide") else "")
        img = f'<img src="{esc(src)}" alt="{esc(x.get("alt", ""))}">'
        if x.get("wide"):
            img = f'<a href="{esc(src)}" target="_blank" title="원본 크기로 열기">{img}</a>'
        return f'<figure class="{cls}">{img}</figure>'
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


def diagram(ctx, b):
    target = f"{ctx.domain}/{b.get('src', '')}"
    if not (ctx.site.docs / target).is_file():
        return f'<p class="note">흐름도 파일({esc(b.get("src", ""))})이 없어요.</p>'
    link = ctx.href(target)
    more = f'<a href="{esc(link)}" target="_blank">새 탭에서 크게 보기</a>' if link != "#" else ""
    return (f'<div class="diagram"><iframe {ctx.frame(target)} title="{esc(b.get("title", ""))}" loading="lazy" '
            f'height="{int(b.get("height", 560))}"></iframe>{more}</div>')


def heading(b):
    hid = f' id="{esc(b["id"])}"' if b.get("id") else ""
    small = f'<small>{esc(b["sub"])}</small>' if b.get("sub") else ""
    return f'<h2{hid}>{esc(b.get("title", ""))}{small}</h2>'


def blocks(ctx, stage, after=None):
    out = []
    for b in stage.get("blocks", []):
        t = b.get("type")
        if ctx.site.hidden("block", t) or (b.get("title") and ctx.site.hidden("block", b["title"])):
            continue
        if t == "cases":
            out.append((heading(b) if b.get("title") else "") + cases(ctx, b) + (after or {}).get(b.get("id"), ""))
        elif t == "diagram":
            out.append(heading(b) + diagram(ctx, b))
        elif t == "checklist":
            out.append(checklist(ctx, b))
        elif t == "routes":
            out.append(routes_block(ctx, b))
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


_SVG = '<svg class="lk-i" viewBox="0 0 16 16" aria-hidden="true">{}</svg>'
LINK_KINDS = [
    # (kind, label, host or label match, label prefixes stripped inside the group, icon)
    ("prd", "기획서", ("기획서", "prd", "notion.so", "notion.site"), ("기획서 · ", "기획서 ", "PRD · ", "PRD "),
     '<path d="M4 1.5h5.5L12.5 4.5V14.5H4z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>'
     '<path d="M6 8h4.5M6 10.5h4.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>'),
    ("jira", "Jira", ("atlassian.net/browse", "jira", "지라"), ("Jira · ", "Jira ", "지라 · ", "지라 "),
     '<path d="M8 1.5 14.5 8 8 14.5 1.5 8z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>'
     '<path d="M8 5.2 10.8 8 8 10.8 5.2 8z" fill="currentColor"/>'),
    ("figma", "Figma", ("figma.com", "figma"), ("Figma · ", "Figma "),
     '<rect x="4" y="1.5" width="4" height="4" rx="2" fill="currentColor"/><rect x="8" y="1.5" width="4" height="4" rx="2" fill="currentColor" opacity=".55"/>'
     '<rect x="4" y="6" width="4" height="4" rx="2" fill="currentColor" opacity=".55"/><circle cx="10" cy="8" r="2" fill="currentColor"/>'
     '<path d="M6 10.5h2v2a2 2 0 1 1-2-2z" fill="currentColor" opacity=".8"/>'),
    ("slack", "Slack", ("slack.com", "slack", "슬랙"), ("Slack · ", "Slack ", "슬랙 · ", "슬랙 "),
     '<path d="M6 2v12M10 2v12M2 6h12M2 10h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'),
    ("confluence", "Confluence", ("atlassian.net/wiki", "confluence"), ("Confluence · ", "Confluence "),
     '<path d="M2 11.5c3-3 6-3 12 0M2 4.5c6 3 9 3 12 0" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'),
    ("github", "GitHub", ("github.com",), ("GitHub · ", "GitHub ", "PR · "),
     '<path d="M5.5 4 1.5 8l4 4M10.5 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'),
    ("other", "링크", (), (),
     '<path d="M7 9a2.5 2.5 0 0 0 3.5 0l2.5-2.5a2.5 2.5 0 0 0-3.5-3.5L8.8 3.7M9 7a2.5 2.5 0 0 0-3.5 0L3 9.5A2.5 2.5 0 0 0 6.5 13l.7-.7" '
     'fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>'),
]


def link_kind(link):
    url, label = link.get("url", "").lower(), link.get("label", "").lower()
    for kind in LINK_KINDS[:-1]:
        if any(m in url for m in kind[2] if "." in m) or any(label.startswith(m) for m in kind[2] if "." not in m):
            return kind
    return LINK_KINDS[-1]


def link_list(links):
    """Links grouped by where they point (기획서 → Jira → Figma → Slack …), one row per kind."""
    groups = {}
    for l in links or []:
        groups.setdefault(link_kind(l), []).append(l)
    rows = []
    for kind in LINK_KINDS:
        items = groups.get(kind)
        if not items:
            continue
        cells = []
        for l in items:
            label = l.get("label", "")
            short = next((label[len(p):] for p in kind[3] if label.startswith(p) and label[len(p):].strip()), label)
            cells.append(f'<a href="{esc(safe_url(l.get("url", "")))}" target="_blank" rel="noopener">{esc(short or l.get("url", ""))}</a>')
        rows.append(f'<li class="lk lk-{kind[0]}"><span class="lk-k">{_SVG.format(kind[4])}{esc(kind[1])}</span>'
                    f'<span class="lk-v">{"".join(cells)}</span></li>')
    return f'<ul class="links">{"".join(rows)}</ul>' if rows else ""


def feature_up(ctx, task):
    """The feature page above a task → (href, title, same docs?, state) or None."""
    ref = task.get("feature") or {}
    fid = ref.get("id")
    if not fid:
        return None
    if fid in ctx.site.features:
        f = ctx.site.features[fid]
        return ctx.href(ctx.site.feature_page(fid)), f.get("title") or fid, True, ctx.site.feature_state(fid)
    doc = feat.feature_doc(ctx.site.docs, ref)
    if doc:
        title = read_json(doc).get("title") or fid
        return (doc.parent / "index.html").as_uri(), title, False, "wait"
    return None


def feature_meta(ctx, task):
    up = feature_up(ctx, task)
    return f'기능 <a href="{esc(up[0])}">{esc(up[1])}</a>' if up else ""


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
    for n, (k, title, fname, keys) in enumerate(task_pages(task), 1):
        if ctx.site.hidden("page", k):
            continue
        s = page_state(task, keys)
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
    feats = []
    for fid, f in site.features.items():
        page = site.feature_page(fid)
        feats.append(f'<a class="tn {site.feature_state(fid)}{" on" if here == page else ""}" href="{ctx.href(page)}">{esc(f.get("title") or fid)}</a>')
    up = feature_up(ctx, site.domains[d]["tasks"][t]) if d and t else None
    if up and not up[2]:
        feats.append(f'<a class="tn {up[3]}" href="{esc(up[0])}">{esc(up[1])}</a>')
    foot = ""
    if d and t:
        links = site.domains[d]["tasks"][t].get("links", [])
        foot = "".join(f'<a href="{esc(safe_url(l.get("url", "")))}" target="_blank" rel="noopener">{esc(l.get("label", ""))}</a>' for l in links)
    return (f'<a class="home" href="{ctx.href(site.root)}">{esc(site.repo)}</a><p class="nav-meta">flow 문서</p>'
            f'<a class="tn root{" on" if here == site.root else ""}" href="{ctx.href(site.root)}">전체 문서</a>'
            f'{"<div class=nav-group>기능</div>" + "".join(feats) if feats else ""}'
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
                if depth == 0 and ((p / "domain.json").exists() or p.name == feat.FEATURES):
                    continue
                if depth < 4:
                    walk(p, depth + 1)
            elif p.suffix in LEGACY_EXT and not is_generated(p):
                out.append(p.relative_to(docs).as_posix())

    walk(docs, 0)
    return out


def legacy_href(rel):
    """Where the index links a legacy file: a .md gets its rendered view page beside it."""
    return rel + ".html" if rel.endswith(".md") else rel


def legacy_view(site, rel, legacy):
    """A page that shows one legacy .md rendered. It sits beside the source, so the document's own
    relative links and images keep working; offline it falls back to the raw text."""
    page = legacy_href(rel)
    ctx = Ctx(site, page)
    base = posixpath.dirname(page) or "."
    md_links = [posixpath.relpath(m, base) for m in legacy if m.endswith(".md")]
    raw = (site.docs / rel).read_text(encoding="utf-8", errors="replace")
    data = json.dumps({"md": raw, "links": md_links}, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\u0021--")
    body = (f'<div class="head"><h1>{esc(posixpath.basename(rel))}</h1>'
            f'<p class="meta">그 밖의 문서 · {esc(rel)} · <a href="{esc(posixpath.basename(rel))}">원문</a></p></div>'
            f'<article class="mdview" id="mdview"><pre>{esc(raw)}</pre></article>'
            f'<script type="application/json" id="md-data">{data}</script>'
            f'<script src="{MARKED}"></script>'
            '<script>(function(){var d=JSON.parse(document.getElementById("md-data").textContent);'
            'if(!window.marked)return;var el=document.getElementById("mdview");el.innerHTML=marked.parse(d.md);'
            'var md=new Set(d.links.map(function(l){return new URL(l,location.href).href}));'
            'el.querySelectorAll("a[href]").forEach(function(a){var u=new URL(a.getAttribute("href"),location.href);'
            'var h=u.hash;u.hash="";if(md.has(u.href))a.setAttribute("href",a.getAttribute("href").split("#")[0]+".html"+h)});'
            # marked 12 emits no heading ids; add GitHub-style slugs so links like spec.md#scope land.
            'var seen={};el.querySelectorAll("h1,h2,h3,h4,h5,h6").forEach(function(x){'
            'var s=x.textContent.trim().toLowerCase().replace(/[^\\p{L}\\p{N}\\s_-]/gu,"").replace(/\\s/g,"-");'
            'var n=seen[s]||0;seen[s]=n+1;x.id=n?s+"-"+n:s});'
            'if(location.hash){var t=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(t)t.scrollIntoView()}})()</script>')
    return shell(ctx, f"{rel} · {site.repo}", nav_tree(ctx), body)


def root_page(site):
    ctx = Ctx(site, site.root)
    rows = []
    for d, dom in site.domains.items():
        active = [(t, task) for t, task in dom["tasks"].items() if task_state(task) != "done"]
        lst = "".join(f'<div><a href="{ctx.href(site.task_page(d, t))}">{esc(t)} {esc(task.get("title", ""))}</a> '
                      f'<span class="st-dot {task_state(task)}">{STATE_LABEL[task_state(task)]}</span></div>' for t, task in active)
        rows.append(f'<div class="row"><h3><a href="{ctx.href(site.domain_page(d))}">{esc(dom["info"].get("title", d))}</a>'
                    f'<small>{esc(d)} · 작업 {len(dom["tasks"])}</small></h3><div>{lst or "<span class=note>진행 중인 작업 없음</span>"}</div></div>')
    frows = []
    for fid, f in site.features.items():
        prog = site.progress(fid)
        lst = "".join(f'<div>{esc(k)} {esc(r.get("title", ""))} <span class="st-dot {row_dot(prog[k])}">{esc(feat.ROW_STATE[prog[k]["state"]])}</span></div>'
                      for r in f.get("rows", []) for k in [feat.row_key(r)])
        frows.append(f'<div class="row"><h3><a href="{ctx.href(site.feature_page(fid))}">{esc(f.get("title") or fid)}</a>'
                     f'<small>{esc(fid)} · 작업 {len(f.get("rows", []))}</small></h3><div>{lst or "<span class=note>아직 줄이 없어요</span>"}</div></div>')
    legacy = legacy_files(site)
    leg = ""
    if legacy:
        leg = ("<h2>그 밖의 문서</h2><ul class=\"legacy-list\">"
               + "".join(f'<li><a href="{esc(ctx.href(legacy_href(p)))}">{esc(p)}</a></li>' for p in legacy) + "</ul>")
    body = (f'<div class="head"><h1>{esc(site.repo)}</h1><p class="meta">도메인 {len(site.domains)} · 그 밖의 문서 {len(legacy)}</p></div>'
            f'{"<h2>기능</h2><div class=cards>" + "".join(frows) + "</div><h2>도메인</h2>" if frows else ""}'
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


def at(text):
    return f' <code class="at">{esc(text)}</code>' if text else ""


def entry_html(ctx, s):
    steps = s.get("entry") or []
    if not steps:
        return ""
    parts = " → ".join(f'{ctx.rich(x.get("text", ""))}{at(x.get("at"))}' if isinstance(x, dict) else ctx.rich(x) for x in steps)
    return f'<p class="meta entry"><b>들어오는 길</b> {parts}</p>'


def pin_chips(ctx, ids, markers):
    out = []
    for i in ids:
        m = markers.get(i)
        label, cls = KIND.get((m or {}).get("kind"), ("?", "pend"))
        out.append(f'<span class="mk k-{cls}">{esc(i[1:])}</span> {ctx.rich(m.get("title", "")) if m else esc(i)}')
    return "<br>".join(out)


def api_boxes(ctx, s, only=None):
    """API → normalising function (file:line) → screen element, one box per call."""
    markers = {m.get("id"): m for m in s.get("markers", [])}
    out = []
    for a in s.get("apis") or []:
        rows = [r for r in a.get("rows", []) if only is None or set(r.get("to") or []) & only]
        if not rows:
            continue
        trs = []
        for r in rows:
            to = r.get("to") or []
            fn = f'<b>{esc(r["fn"])}</b>' if r.get("fn") else '<span class="note">정규화 없음</span>'
            rule = f'<div class="nt">{copy_marks(ctx.rich(r["rule"]))}</div>' if r.get("rule") else ""
            di = f' data-i="{esc(to[0])}"' if to else ""
            trs.append(f'<tr{di}><td><code>{esc(r.get("field", ""))}</code></td><td>{fn}{at(r.get("at"))}{rule}</td>'
                       f'<td>{pin_chips(ctx, to, markers)}</td></tr>')
        via = f'<p class="note">{ctx.rich(a["via"])}{" → <code>" + esc(a["type"]) + "</code>" if a.get("type") else ""}</p>' if a.get("via") else ""
        out.append(f'<h3>API · <code>{esc(a.get("call", ""))}</code></h3>{via}<table class="flowmap"><thead><tr><th>응답 필드</th>'
                   f'<th>정규화 · 위치</th><th>화면 요소</th></tr></thead><tbody>{"".join(trs)}</tbody></table>')
    return "".join(out)


def param_boxes(ctx, s):
    """URL query · path params · navigation values ↔ the UI that sets them → the API request value."""
    out = []
    for p in s.get("params") or []:
        trs = []
        for r in p.get("rows", []):
            default = f'<div class="nt todo">{copy_marks(ctx.rich(r["default"]))}</div>' if r.get("default") else ""
            req_rule = f'<div class="nt todo">{copy_marks(ctx.rich(r["rule"]))}</div>' if r.get("rule") else ""
            trs.append(f'<tr><td><code>{esc(r.get("param", ""))}</code>{at(r.get("paramAt"))}{default}</td>'
                       f'<td>↔ {ctx.rich(r.get("ui", ""))}{at(r.get("uiAt"))}</td>'
                       f'<td>→ {ctx.rich(r.get("request", ""))}{at(r.get("requestAt"))}{req_rule}</td></tr>')
        call = f' · <code>{esc(p["call"])}</code>' if p.get("call") else ""
        via = f'<p class="note">{ctx.rich(p["via"])}</p>' if p.get("via") else ""
        note = f'<p class="note">{copy_marks(ctx.rich(p["note"]))}</p>' if p.get("note") else ""
        out.append(f'<h3>파라미터{call}</h3>{via}<table class="flowmap"><thead><tr><th>파라미터 · 기본값</th><th>UI</th>'
                   f'<th>API 요청 값 · 변환</th></tr></thead><tbody>{"".join(trs)}</tbody></table>{note}')
    return "".join(out)


def routes_block(ctx, b):
    trs = "".join(f'<tr><td><code>{esc(r.get("path", ""))}</code></td><td>{ctx.rich(r.get("name", "")) or "<span class=note>—</span>"}</td>'
                  f'<td><code>{esc(r.get("file", ""))}</code></td><td>{" ".join(f"<code>{esc(x)}</code>" for x in r.get("sheets", [])) or "—"}</td>'
                  f'<td>{"<br>".join(f"<code>{esc(x)}</code>" for x in r.get("apis", [])) or "<span class=note>확인 전</span>"}</td></tr>'
                  for r in b.get("rows", []))
    return (f'{heading({**b, "title": b.get("title") or "작업 경로 맵", "sub": b.get("sub") or "경로 · 시트는 스크립트가 뽑고, API는 이 작업에서 확인한 것만"})}'
            f'<table class="tbl"><thead><tr><th>경로</th><th>기능</th><th>파일</th><th>시트</th><th>API</th></tr></thead><tbody>{trs}</tbody></table>')


def sot_map(ctx, d, only=None):
    """The domain's SOT map; with `only`, just the screens and rows whose IDs are in it."""
    dom = ctx.site.domains[d]
    sot = dom["screens"]
    comp = dom["info"].get("kind") == "components"
    field_head = "속성 · 토큰" if comp else "서버 필드"
    off_intro = "Figma에 그려지지 않았지만 코드가 다뤄야 하는 경우예요." if comp else "Figma 화면에는 없지만 데이터 때문에 생기는 경우예요."
    used = used_by(ctx, d)
    counts, parts = {}, []
    for f in sot.get("flows", []) if only is None else []:
        rows = "".join(f"<tr><td>{ctx.rich(a)}</td><td>{ctx.rich(b)}</td></tr>" for a, b in f.get("rows", []))
        parts.append(f'<h2>흐름 · {esc(f.get("title", ""))}</h2><table><thead><tr><th>언제</th><th>결과</th></tr></thead><tbody>{rows}</tbody></table>')
    for s in sot.get("screens", []):
        markers = [m for m in s.get("markers", []) if only is None or m.get("id") in only]
        offscreen = [o for o in s.get("offscreen", []) if only is None or o.get("id") in only]
        if only is not None and not markers and not offscreen:
            continue
        frame = None
        meta = dom["dir"] / s.get("metadata", "")
        if s.get("metadata") and meta.exists():
            frame = frame_boxes(meta)
        pins, groups = [], []
        for m in markers:
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
        if offscreen:
            orows = "".join(f'<tr id="{esc(o["id"])}"><td><span class="mk k-out">{esc(o["id"])}</span></td><td><b>{ctx.rich(o.get("state", ""))}</b>'
                            f'{used_html(used.get(o["id"]))}</td><td>{ctx.rich(o.get("when", ""))}</td><td>{ctx.rich(o.get("shows", ""))}</td></tr>'
                            for o in offscreen)
            off = (f'<h3>화면 밖 상태</h3><p class="note">{esc(s.get("offscreenIntro") or off_intro)}</p><table><thead><tr><th></th>'
                   f'<th>상태</th><th>언제</th><th>보이는 것</th></tr></thead><tbody>{orows}</tbody></table>')
        variants = ""
        if s.get("variants"):
            vrows = "".join(f'<tr><td><b>{esc(v.get("axis", ""))}</b></td><td>{ctx.rich(v.get("values", ""))}</td><td>{ctx.rich(v.get("prop", ""))}</td>'
                            f'<td>{ctx.rich(v.get("note", ""))}</td></tr>' for v in s["variants"])
            variants = f'<h3>변형 축</h3><table class="tbl"><thead><tr><th>Figma 축</th><th>값</th><th>코드 속성</th><th>메모</th></tr></thead><tbody>{vrows}</tbody></table>'
        land = frame and (frame[0] > frame[1] or frame[0] > 700)
        if frame:
            shot = (f'<div class="shot"><div class="fig" data-w="{frame[0]:g}" data-h="{frame[1]:g}"><img src="{esc(ctx.href(f"{d}/{s.get('image', '')}"))}" '
                    f'alt="{esc(s.get("title", ""))} Figma 화면">{"".join(pins)}</div></div>')
        else:
            shot = f'<div class="shot"><p class="note">구조 정보({esc(s.get("metadata", ""))})를 읽지 못했어요.</p></div>'
        parts.append(f'<h2 class="screen" id="screen-{esc(s.get("id", ""))}">{"컴포넌트" if comp else "화면"} · {esc(s.get("title", ""))}</h2>'
                     f'<p class="meta">Figma <code>{esc(s.get("figma", ""))}</code></p>{entry_html(ctx, s)}<div class="cols{" landscape" if land else ""}">{shot}<div>{variants}{tables}{off}</div></div>'
                     f'{api_boxes(ctx, s, only)}{param_boxes(ctx, s)}')
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
                "answer": {k: a.get(k, "") for k in ("choice", "why", "note", "followUp", "copy")},
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


def task_index(site, d, t, shared=None):
    dom = site.domains[d]
    task = dom["tasks"][t]
    ctx = Ctx(site, site.task_page(d, t), d, t)
    cards, skipped = [], []
    for n, (k, title, fname, keys) in enumerate(task_pages(task), 1):
        if site.hidden("page", k):
            continue
        s = page_state(task, keys)
        if s["status"] == "skip":
            skipped.append(f"{n} {title}")
            continue
        if k == "grill":
            lis = grill_conclusion(ctx, task["stages"]["grill"], s)
        else:
            lis = "".join(f"<li>{ctx.rich(c)}</li>" for c in page_conclusion(task, keys)) or "<li>아직 없어요.</li>"
        cards.append(f'<section class="stage-card {s["status"]}"><h2><a href="{fname}"><span class="n">{n}</span>{esc(title)}</a>'
                     f'<span class="st">{esc(plain_refs(s["summary"]))}</span></h2>{f"<ul>{lis}</ul>" if lis else ""}</section>')
    meta = " · ".join(x for x in (feature_meta(ctx, task), esc(dom["info"].get("title", d)), esc(t), esc(task.get("type", "")),
                                  f"<code>{esc(task['branch'])}</code>" if task.get("branch") else "") if x)
    note = f'<p class="note">건너뛴 단계: {esc(", ".join(skipped))}. 필요해지면 그때 만들어요.</p>' if skipped else ""
    if task.get("followUps"):
        rows = "".join(f'<tr><td>{esc(x.get("date", ""))}</td><td>{copy_marks(ctx.rich(x.get("text", "")))}</td>'
                       f'<td>{" ".join(f"<code>{esc(p)}</code>" for p in x.get("files", []))}</td><td><code>{esc(x.get("sha", ""))}</code></td></tr>'
                       for x in task["followUps"])
        note += (f'<h2>후속 수정<small>작업이 끝난 뒤 이 작업의 파일을 고친 기록</small></h2><table class="tbl"><thead><tr>'
                 f'<th>날짜</th><th>내용</th><th>파일</th><th>커밋</th></tr></thead><tbody>{rows}</tbody></table>')
    body = (f'<div class="head">{export_menu(ctx, d, t, shared)}<h1>{esc(task.get("title", t))}</h1><p class="meta">{meta}</p></div>{link_list(task.get("links"))}'
            f'{intent_section(ctx, task)}{unconfirmed_section(ctx, task)}{"".join(cards)}{note}')
    return shell(ctx, f"{t} {task.get('title', '')} · flow", nav_tree(ctx, d, t), body, shared=shared)


def needs_answer(q):
    return not q.get("decision") or (q.get("answer") or {}).get("by") == "user"


def question_homes(stage):
    """Question tag → the cases block it belongs under: rows that ask it first, then the 케이스 context."""
    homes, owner = {}, {}
    for b in stage.get("blocks", []):
        if b.get("type") != "cases" or not b.get("id"):
            continue
        owner[b["id"]] = b["id"]
        for row in b.get("rows", []):
            if row.get("id"):
                owner[row["id"]] = b["id"]
            for tag in [row.get("ask")] + [ch.get("q") for ch in row.get("status", []) if isinstance(ch, dict)]:
                if tag:
                    homes.setdefault(tag, b["id"])
    for r in stage.get("rounds", []):
        for q in r.get("questions", []):
            tag = f"{r['id']}-{q['id']}"
            if tag in homes:
                continue
            text = " ".join(str(v) for k, v in q.get("context", []) if k == "케이스")
            hit = next((owner[m.group(1)] for m in REF.finditer(text) if m.group(1) in owner), None)
            if hit:
                homes[tag] = hit
    return homes


def grill_conclusion(ctx, stage, s):
    """One line per question still needing a person; empty once every round is closed."""
    if not stage.get("rounds"):
        return "<li>아직 질문이 없어요.</li>"
    out = []
    for r in stage["rounds"]:
        for q in r.get("questions", []):
            if not needs_answer(q):
                continue
            chip = ('<span class="k ans">답이 바뀜 · 반영 전</span>' if q.get("decision")
                    else '<span class="k ans">답 받음 · 반영 전</span>' if (q.get("answer") or {}).get("by") == "user"
                    else '<span class="k pend">답 대기</span>')
            out.append(f'<li class="wait-q">{ctx.rich(f"[[{r["id"]}-{q["id"]}]]")} {ctx.rich(q.get("title", ""))}{chip}</li>')
    return "".join(out)


INTENT_STATE = {"guess": "가설", "confirmed": "확인됨"}


def intent_section(ctx, task):
    items = task.get("intent") or []
    if not items:
        return ""
    lis = []
    for it in items:
        st = it.get("state", "guess")
        was = "".join(f'<li class="was">{ctx.rich(w)}</li>' for w in it.get("was", []))
        basis = f'<span class="basis">{ctx.rich(it["basis"])}</span>' if it.get("basis") else ""
        lis.append(f'<li class="{esc(st)}"><span class="k {"done" if st == "confirmed" else "pend"}">{esc(INTENT_STATE.get(st, st))}</span>'
                   f'{ctx.rich(it.get("text", ""))}{basis}{f"<ul>{was}</ul>" if was else ""}</li>')
    return (f'<section class="intent-card"><h2>이 기능의 의도<small>무엇을 위해 만드는지 · 답을 받을 때마다 고쳐 써요</small></h2>'
            f'<ul>{"".join(lis)}</ul></section>')


def question_card(ctx, r, q):
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
    ctxl = f'<ul class="q-ctx">{ctxl}</ul>' if ctxl and not ctx.site.hidden("field", "context") else ""
    said = f'<div class="said">{ctx.rich(q["said"])}</div>' if q.get("said") and not ctx.site.hidden("field", "said") else ""
    intent = f'<div class="intent"><b>왜 묻나요</b>{ctx.rich(q["intent"])}</div>' if q.get("intent") else ""
    body = f'<div>{ctx.rich(q["body"])}</div>' if q.get("body") and not ctx.site.hidden("field", "body") else ""
    to = q.get("to") or []
    to = [to] if isinstance(to, str) else to
    badge += "".join(f'<span class="k to">{esc(AUDIENCE.get(w, w))}</span>' for w in to)
    cp = q.get("copy")
    copy_fld = (f'<label class="fld"><span>{esc(cp.get("label", "문구"))} · 줄바꿈 그대로</span><textarea data-f="copy" '
                f'placeholder="{esc(cp.get("placeholder", "화면에 보일 문구 그대로"))}">{esc(a.get("copy", ""))}</textarea></label>') if cp else ""
    tpls = "".join(f'<template data-preview="{esc(k)}">{mocks_html(ctx, v if isinstance(v, list) else [v])}</template>'
                   for k, v in (q.get("preview") or {}).items()) if not ctx.site.hidden("field", "preview") else ""
    live = f'<div class="live" data-live>{tpls}</div>' if tpls else ""
    # A wide capture beside the options squeezes them to one character per line; put it under them.
    shots = [m for v in (q.get("preview") or {}).values() for m in (v if isinstance(v, list) else [v])]
    wide_live = any(isinstance(m.get("shot"), dict) and m["shot"].get("wide") for m in shots if isinstance(m, dict))
    below = live if wide_live else ""
    live = "" if wide_live else live
    note_fld = ("" if ctx.site.hidden("field", "note") else
                f'<label class="fld"><span>메모</span><textarea data-f="note" placeholder="다르게 고르면 조건을 적어 주세요">{esc(a.get("note", ""))}</textarea></label>')
    follow_fld = ("" if ctx.site.hidden("field", "followUp") else
                  f'<label class="fld"><span>되묻기</span><textarea data-f="followUp" placeholder="되묻고 싶은 것">{esc(a.get("followUp", ""))}</textarea></label>')
    rs = q.get("reason") or {}
    reason = (f'<div class="reason"><b>고른 이유 · {esc(REASON_BY.get(rs.get("by"), rs.get("by", "")))}</b>{ctx.rich(rs.get("text", ""))}</div>'
              if rs.get("text") else "")
    decision = (f'<div class="decision"><b>결정</b>{ctx.rich(q["decision"])}{reason}<div class="applied">반영한 곳: {ctx.rich(q.get("appliedTo", ""))}</div></div>'
                if q.get("decision") else "")
    form = (f'{said}{body}<div class="rec-line"><b>추천</b>{ctx.rich(q.get("recommendation", ""))}</div>'
            f'<div class="q-grid{" has-live" if live else ""}"><div><div class="opts">{radios}</div>{below}{copy_fld}'
            f'<label class="fld"><span>이렇게 고른 이유</span><textarea data-f="why" placeholder="무엇을 지키고 싶어서 이 답을 골랐는지">{esc(a.get("why", ""))}</textarea></label>'
            f'{note_fld}{follow_fld}</div>{live}</div>')
    if needs_answer(q):
        inner = f"{intent}{ctxl}{form}{decision}"
    else:
        picked = next((o["label"] for o in opts if o["value"] == a.get("choice")), "")
        lead = f"고른 답 · {esc(picked)}" if picked else "질문과 답"
        inner = f'{intent}{ctxl}{decision}<details class="q-more"><summary>{lead} — 펼쳐서 보거나 고쳐요</summary>{form}</details>'
    cls = "q open" if not q.get("decision") and a.get("by") != "user" else "q"
    return (f'<div class="{cls}" id="{esc(tag)}" data-tag="{esc(tag)}"><div class="q-head"><b>{esc(tag)}. {ctx.rich(q.get("title", ""))}</b>{badge}</div>'
            f'{inner}</div>')


def grill_body(ctx, stage, s):
    homes = question_homes(stage)
    has_cases = any(b.get("type") == "cases" for b in stage.get("blocks", []))
    under, loose, past, anchored = {}, [], [], set()
    for r in stage.get("rounds", []):
        for q in r.get("questions", []):
            if not needs_answer(q):
                continue
            tag = f"{r['id']}-{q['id']}"
            mark = f'<a id="{esc(r["id"])}"></a>' if r["id"] not in anchored else ""
            anchored.add(r["id"])
            card = mark + question_card(ctx, r, q)
            if tag in homes:
                under.setdefault(homes[tag], []).append(card)
            else:
                loose.append(card)
    for r in reversed(stage.get("rounds", [])):
        done = [q for q in r.get("questions", []) if not needs_answer(q)]
        if not done:
            continue
        rid = "" if r["id"] in anchored else f' id="{esc(r["id"])}"'
        past.append(f'<details class="past"{rid}{"" if has_cases else " open"}><summary><b>{esc(r["id"])}</b> {esc(r.get("askedAt", ""))} · {ctx.rich(r.get("from", ""))}'
                    f' · <span class="note">질문 {len(done)}개</span></summary>{"".join(question_card(ctx, r, q) for q in done)}</details>')
    after = {k: f'<div class="case-qs">{"".join(v)}</div>' for k, v in under.items()}
    lis = grill_conclusion(ctx, stage, s)
    out = (conclusion(ctx, s["status"], lis=lis) if lis else "") + blocks(ctx, stage, after)
    if loose:
        title = "그 밖의 질문" if after or stage.get("blocks") else "질문"
        out += f'<h2>{title}<small>케이스 표에 묶이지 않은 질문</small></h2><div class="case-qs">{"".join(loose)}</div>'
    if past:
        out += f'<h2>지난 질문<small>결정됨 · 답을 바꾸려면 펼쳐서 고쳐요</small></h2><div class="pasts">{"".join(past)}</div>'
    return out


def task_sot_ids(domain, task):
    seen = set()

    def visit(raw, owner):
        rd, rt, item = parse_ref(raw, domain, task["id"])
        if rd == domain and rt is None and item and re.fullmatch(r"[SX]\d+", item):
            seen.add(item)

    walk_refs(task.get("stages") or {}, None, visit)
    return seen


def screen_refs(ctx, task):
    seen = task_sot_ids(ctx.domain, task)
    full = f'<a href="{ctx.href(ctx.site.domain_page(ctx.domain))}">도메인 SOT 맵 전체</a>'
    if not seen:
        return f"<h2>SOT 맵</h2><p>이 작업이 가리키는 행이 아직 없어요. {full}</p>"
    return f'<p class="meta">이 작업이 가리키는 화면과 행만 보여요 · {full}</p>{sot_map(ctx, ctx.domain, seen)}'


def page_conclusion(task, keys):
    stages = task.get("stages") or {}
    return [c for k in keys if k in stages for c in stages[k].get("conclusion") or []]


def unconfirmed_section(ctx, task):
    """What went in without a person — kept in the record so anyone can tell it apart from what was confirmed."""
    u = unconfirmed(task)
    if not any(u.values()):
        return ""
    lis = [f'<li><span class="k out">건너뛴 멈춤</span> {esc(STAGE_TITLE.get(x.get("stage"), x.get("stage", "")))} · '
           f'{esc(x.get("stop", ""))}{(" — " + esc(x["why"])) if x.get("why") else ""}</li>' for x in u["skipped"]]
    def ref(i):
        return ctx.rich(f"[[{i}]]") if ITEM_ID.match(i) else f"<code>{esc(i)}</code>"
    if u["inferred"]:
        lis.append(f'<li><span class="k pend">추정</span> {" ".join(ref(i) for i in u["inferred"])}</li>')
    lis += [f'<li><span class="k out">모름</span> {ref(i)} — {esc(why)}</li>' for i, why in u["unknown"]]
    return (f'<h2>사람 확인 없이 남은 것<small>사람이 보기 전에 Claude가 대화 · 코드로 채운 것과, 아무도 알 수 없어 비운 것</small></h2>'
            f'<ul class="check">{"".join(lis)}</ul>')


def attached(ctx, key, st):
    """Everything attached to a core stage — stages.<key>.ext.<id> — whoever attached it. The title and
    field names come from the task itself, so a teammate without the attaching person's settings reads it
    the same way; the settings only add the fields still missing."""
    ext_all = st.get("ext") if isinstance(st.get("ext"), dict) else {}
    mine = {a["plugin"]: a for a in ctx.site.workflow["attach"] if a["stage"] == key}
    out = ""
    for pid in list(dict.fromkeys([*mine, *ext_all])):
        ext = ext_all.get(pid) if isinstance(ext_all.get(pid), dict) else {}
        a = mine.get(pid)
        unknown = ext.get("unknown") if isinstance(ext.get("unknown"), dict) else {}
        inferred = set(ext.get("inferred") or [])
        names = list(dict.fromkeys((a["fields"] if a else []) + [k for k in ext if k not in ("title", "unknown", "inferred")]
                                   + list(unknown)))
        rows = []
        for f in names:
            if f in ext:
                v = ext[f]
                val = esc(v) if isinstance(v, (str, int, float)) else f"<code>{esc(json.dumps(v, ensure_ascii=False))}</code>"
                tag = ' <span class="k pend">추정</span>' if f in inferred else ""
            elif f in unknown:
                val, tag = "", f' <span class="k out">모름 · {esc(unknown[f])}</span>'
            else:
                val, tag = '<span class="note">아직 없어요</span>', ""
            rows.append(f"<tr><td><code>{esc(f)}</code></td><td>{val}{tag}</td></tr>")
        title = str(ext.get("title") or (a and a["title"]) or pid)
        out += (f'<h2>붙임 · {esc(title)}<small>{esc(pid)} · stages.{esc(key)}.ext.{esc(pid)}</small></h2>'
                f'<table class="tbl"><tbody>{"".join(rows) or "<tr><td>아직 없어요</td></tr>"}</tbody></table>')
    return out


def stage_page(site, d, t, page, n, shared=None):
    task = site.domains[d]["tasks"][t]
    ctx = Ctx(site, site.task_page(d, t, page), d, t)
    _, title, _, keys = next(x for x in task_pages(task) if x[0] == page)
    stages = task["stages"]
    s = page_state(task, keys)
    if page == "grill":
        body = grill_body(ctx, stages["grill"], s) + attached(ctx, "grill", stages["grill"])
    else:
        body = conclusion(ctx, s["status"], page_conclusion(task, keys))
        body += "".join(blocks(ctx, stages[k]) + attached(ctx, k, stages[k]) for k in keys if k in stages)
        if "screen" in stages and "screen" in keys:
            part = f'<h2 class="part">{esc(STAGE_TITLE["screen"])}</h2>' if any(k in stages for k in keys if k != "screen") else ""
            body += part + screen_refs(ctx, task)
    head = (f'<div class="head">{export_menu(ctx, d, t, shared)}<h1><span class="n {s["status"]}">{n}</span>{esc(title)}</h1>'
            f'<p class="meta">{" · ".join(x for x in (feature_meta(ctx, task), esc(task.get("title", t)), esc(t), esc(plain_refs(s["summary"]))) if x)}</p></div>')
    return shell(ctx, f"{n} {title} · {task.get('title', t)}", nav_tree(ctx, d, t, page), head + body,
                 wide="screen" in keys and "screen" in stages, answers=answers_data(site, d, t), shared=shared)


# ---------------------------------------------------------------- feature page

def row_dot(prog):
    if prog["task"]:
        return task_state(prog["task"])
    return "ask" if prog["state"] == "legacy" else "wait"


def row_task_link(ctx, row, prog):
    """Link to the row's task pages: relative in this checkout, absolute in another worktree."""
    tid, d = row.get("task"), row.get("domain")
    if not tid:
        return esc(feat.row_key(row))
    if prog["where"] == "이 체크아웃" and d in ctx.site.domains and tid in ctx.site.domains[d]["tasks"]:
        return f'<a href="{esc(ctx.href(ctx.site.task_page(d, tid)))}">{esc(tid)}</a>'
    wt = feat.row_worktree(ctx.site.docs, row)
    if wt:
        page = Path(wt) / feat.docs_rel(ctx.site.docs) / d / tid / "index.html"
        return f'<a href="{esc(page.as_uri())}" title="다른 워크트리 — 그 워크트리에서 flow.py build 후 열려요">{esc(tid)}</a>'
    return esc(tid)


def stage_chain(prog):
    if not prog["stages"]:
        return '<span class="note">—</span>'
    return " ".join(f'<span class="st-dot {s["status"]}" title="{esc(plain_refs(s["summary"]))}">{esc(k)}</span>'
                    for k, s in prog["stages"])


def feature_page(site, fid):
    f = site.features[fid]
    ctx = Ctx(site, site.feature_page(fid))
    prog = site.progress(fid)
    rows = f.get("rows", [])
    draft = [r for r in rows if not r.get("approved")]
    banner = ""
    if draft:
        banner = (f'<div class="banner"><p>초안이에요 — 승인 전인 줄 {len(draft)}개. 승인하면 <code>flow.py start</code>가 '
                  '지라 하위 이슈 · 워크트리 · 브랜치 · flow 작업을 만들어요.</p></div>')
    snaps = " · ".join(f'{esc(p.get("label", "기획서"))} 스냅샷 {esc(str(p.get("lastEdited", ""))[:10])}' for p in f.get("prd") or [] if p.get("snapshot"))
    home = f.get("home") or {}
    meta = " · ".join(x for x in (f"기능 <code>{esc(fid)}</code>", f"루트 <code>{esc(f['root'])}</code>" if f.get("root") else "",
                                  f"문서 위치 <code>{esc(home['branch'])}</code>" if home.get("branch") else "", snaps) if x)
    links = [{"label": p.get("label", "기획서"), "url": p["url"]} for p in f.get("prd") or [] if p.get("url")] + (f.get("links") or [])
    scope = "".join(f"<li>{ctx.rich(x)}</li>" for x in f.get("scope") or [])
    scope = f'<h2>전체 범위</h2><ul>{scope}</ul>' if scope else ""
    trs = []
    for r in rows:
        k = feat.row_key(r)
        p = prog[k]
        cnt = f'{p["count"][0]}/{p["count"][1]}' if p["count"] else "—"
        jira = (r.get("jira") or {})
        jira_cell = esc(jira.get("status") or "—")
        notes = []
        if p["next"]:
            notes.append(esc(p["next"]))
        if p["blockers"]:
            notes.append(f"blocker {p['blockers']}건")
        todo = f'<div class="todo">{esc(jira["todo"])}</div>' if jira.get("todo") else ""
        story = f'{esc(r.get("story", ""))}<br><span class="note">{esc(r.get("storyTitle", ""))}</span>' if r.get("story") else "—"
        branch = r.get("branch") or (p["task"] or {}).get("branch")
        where = f'<code>{esc(branch)}</code>' if branch else '<span class="note">만들기 전</span>'
        wt = feat.row_worktree(site.docs, r)
        if wt:
            where += f'<br><span class="note">{esc(wt)}</span>'
        trs.append(f'<tr{" class=ask" if not r.get("approved") else ""}><td><b>{row_task_link(ctx, r, p)}</b> {esc(r.get("title", ""))}'
                   f'<br><span class="st-dot {row_dot(p)}">{esc(feat.ROW_STATE[p["state"]])}</span>'
                   f'{"<div class=nt>" + " · ".join(notes) + "</div>" if notes else ""}{todo}</td>'
                   f'<td>{story}</td><td>{where}</td><td class="chain">{stage_chain(p)}</td><td>{cnt}</td><td>{jira_cell}</td></tr>')
    table = (f'<h2>작업<small>진행도는 각 줄의 flow 작업에서 읽어요</small></h2><table class="feat"><thead><tr><th>작업</th><th>스토리</th>'
             f'<th>브랜치 · 워크트리</th><th>flow 단계</th><th>체크</th><th>지라</th></tr></thead><tbody>{"".join(trs)}</tbody></table>') if trs else ""
    sections, missing = feat.section_matrix(site.docs, f, prog)
    matrix = ""
    if sections or missing:
        keys = [feat.row_key(r) for r in rows]
        head = "".join(f"<th>{esc(k)}</th>" for k in keys)
        mrows = []
        labels = {p.get("snapshot"): p.get("label", "기획서") for p in f.get("prd") or []}
        group = len({s[0] for s in sections}) > 1
        last = None
        for snap, num, title, leaf, owners in sections:
            if group and snap != last:
                mrows.append(f'<tr class="grp"><td colspan="{len(keys) + 1}"><b>{esc(labels.get(snap, snap))}</b> '
                             f'<span class="note">{esc(snap)}</span></td></tr>')
                last = snap
            gap = leaf and not owners
            cells = "".join(f'<td class="mx">{"●" if k in owners else ""}</td>' for k in keys)
            label = f'{"" if leaf else "<b>"}{esc(num)}. {esc(title)}{"" if leaf else "</b>"}'
            mrows.append(f'<tr{" class=ask" if gap else ""}><td>{label}{"<div class=todo>주인 없는 섹션</div>" if gap else ""}</td>{cells}</tr>')
        notes = {"absent": "스냅샷에 없는 섹션 — 기획서가 바뀌었거나 번호가 틀려요",
                 "ambiguous": "기획서 여러 개에 같은 번호가 있어요 — sections에 <code>&lt;스냅샷&gt;#</code>을 붙이거나 줄에 <code>prd</code>를 적어 주세요"}
        for num, owners, why in missing:
            cells = "".join(f'<td class="mx">{"●" if k in owners else ""}</td>' for k in keys)
            mrows.append(f'<tr class="ask"><td>{esc(num)}<div class="todo">{notes[why]}</div></td>{cells}</tr>')
        matrix = (f'<h2>기획 섹션 × 작업<small>줄의 sections와 각 작업 기획 인용의 출처에서 점을 찍어요</small></h2>'
                  f'<table class="feat matrix"><thead><tr><th>기획 섹션</th>{head}</tr></thead><tbody>{"".join(mrows)}</tbody></table>')
    extra = ""
    for key, title, cols, fields in (
            ("copy", "사용자 노출 문구", ["화면", "언제", "형태", "문구", "작업"], ["where", "when", "kind", "text", "row"]),
            ("shared", "범위 간 공유물", ["항목", "쓰는 곳", "근거", "만드는 곳", "상태"], ["item", "usedBy", "evidence", "buildIn", "status"]),
            ("componentDiffs", "공유 컴포넌트 차이", ["컴포넌트", "차이", "보고한 곳", "판단"], ["component", "diff", "reportedBy", "decision"]),
            ("questions", "남은 질문", ["작업", "질문"], ["row", "text"]),
            ("log", "기록", ["날짜", "내용"], ["date", "text"])):
        items = f.get(key) or []
        if not items:
            continue
        def cell(v):
            return copy_marks(ctx.rich(", ".join(v) if isinstance(v, list) else v))
        if key == "copy" and not any(it.get("when") or it.get("kind") for it in items):
            cols, fields = ["위치", "문구", "작업"], ["where", "text", "row"]
        body = "".join("<tr>" + "".join(f"<td>{cell(it.get(x, ''))}</td>" for x in fields) + "</tr>" for it in items)
        extra += f'<h2>{title}</h2><table class="tbl wrap"><thead><tr>{"".join(f"<th>{c}</th>" for c in cols)}</tr></thead><tbody>{body}</tbody></table>'
    jpath = (f.get("jira") or {}).get("path") or []
    if jpath:
        steps = " → ".join(f'{"<b>" if s.get("mark") else ""}{esc(s["status"])}{"</b>" if s.get("mark") else ""}'
                           + (f' <span class="note">({esc(s["via"])}, 사람이 옮김)</span>' if s.get("manual") else "") for s in jpath)
        extra += f'<h2>지라 전환<small>굵은 단계까지 flow가 한 단계씩 옮겨요</small></h2><p>{steps}</p>'
    body = (f'<div class="head"><h1>{esc(f.get("title") or fid)}</h1><p class="meta">{meta}</p></div>{banner}{link_list(links)}'
            f'{scope}{table}{matrix}{extra}')
    return shell(ctx, f"{f.get('title') or fid} · flow", nav_tree(ctx), body, wide=True)


# ---------------------------------------------------------------- build

def render_all(docs):
    """→ {path relative to docs: html} for every page the JSON defines."""
    import share
    site = Site(docs)
    pages = {site.root: root_page(site)}
    for fid in site.features:
        pages[site.feature_page(fid)] = feature_page(site, fid)
    for d, dom in site.domains.items():
        pages[site.domain_page(d)] = domain_page(site, d)
        for t, task in dom["tasks"].items():
            shared = None
            if share.wanted(task):
                shared = share.texts(site, d, t)
            pages[site.task_page(d, t)] = task_index(site, d, t, shared)
            for n, (page, _, _, keys) in enumerate(task_pages(task), 1):
                if any(k in (task.get("stages") or {}) for k in keys) and not site.hidden("page", page):
                    pages[site.task_page(d, t, page)] = stage_page(site, d, t, page, n, shared)
    legacy = legacy_files(site)
    for rel in legacy:
        if rel.endswith(".md"):
            pages[legacy_href(rel)] = legacy_view(site, rel, legacy)
    return site, pages


def orphans(site, pages):
    """Generated pages on disk that the JSON no longer defines."""
    out = []
    for d, dom in site.domains.items():
        for sub in sorted(p for p in dom["dir"].iterdir() if p.is_dir() and p.name not in ("tasks", "images", "diagrams", "verify")):
            for f in sorted(sub.glob("*.html")):
                rel = f.relative_to(site.docs).as_posix()
                if rel not in pages and is_generated(f):
                    out.append(rel)
    fdir = site.docs / feat.FEATURES
    if fdir.is_dir():
        for f in sorted(fdir.glob("*/index.html")):
            rel = f.relative_to(site.docs).as_posix()
            if rel not in pages and is_generated(f):
                out.append(rel)
    for f in sorted(site.docs.rglob("*.md.html")):
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


IGNORE_BEGIN = "# flow:begin — flow.py build writes these; never committed"
IGNORE_END = "# flow:end"


def ignore_lines(site):
    lines = [f"/{site.root}"]
    for d in site.domains:
        lines += [f"/{d}/index.html", f"/{d}/*/", f"!/{d}/tasks/", f"!/{d}/images/", f"!/{d}/diagrams/", f"!/{d}/verify/", f"/{d}/diagrams/.receipts/"]
    lines.append(f"/{feat.FEATURES}/*/index.html")
    lines.append("*.md.html")
    return lines


def write_ignore(site):
    path = site.docs / ".gitignore"
    old = path.read_text() if path.exists() else ""
    block = "\n".join([IGNORE_BEGIN, *ignore_lines(site), IGNORE_END]) + "\n"
    if IGNORE_BEGIN in old and IGNORE_END in old:
        head, rest = old.split(IGNORE_BEGIN, 1)
        tail = rest.split(IGNORE_END, 1)[1].lstrip("\n")
        new = head + block + tail
    else:
        new = old + ("\n" if old and not old.endswith("\n") else "") + block
    if new != old:
        path.write_text(new)


def build(docs):
    site, pages = render_all(docs)
    write_ignore(site)
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
