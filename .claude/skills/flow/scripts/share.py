"""Export one task for people outside the flow — 기획 · 디자인 or 백엔드 — as one HTML file or Markdown."""
import base64
import copy
import datetime
import html
import mimetypes
import re
from pathlib import Path

from model import DEFAULT_OPTIONS, REF, parse_ref, plain, read_json
from render import (FONTS, Ctx, Site, asset, blocks, cases, copy_marks, esc, heading, mock_theme, mocks_html,
                    needs_answer, question_homes)

AUDIENCES = {"plan": "기획 · 디자인", "backend": "백엔드"}
ASK = {"plan": ("확인 요청", "확인할 것", "질문"), "backend": ("요청", "요청할 것", "요청")}
TECH_KEYS = {"enum", "서버", "백엔드", "코드", "api", "앱 코드", "스키마"}


def headline(site, d, task, who, n):
    title, count_word, word = ASK[who]
    stamp = site.domains[d].get("mtimes", {}).get(task["id"])
    day = datetime.date.fromtimestamp(stamp) if stamp else datetime.date.today()
    when = f"{day.month}/{day.day} 기준"
    if n:
        return f"{AUDIENCES[who]} {title} · {when} · {count_word} {n}건", f"답은 이 파일을 받은 스레드에 “{word} 번호”와 함께 남겨 주세요."
    lead = "질문은 모두 정해졌어요. 아래 표가 확정된 내용이에요." if who == "plan" else "지금 요청할 것은 없어요. 아래는 이미 정한 내용이에요."
    return f"{AUDIENCES[who]} 공유 · 확정본 · {when}", lead


def diagrams(task):
    plan = (task.get("stages") or {}).get("plan") or {}
    return [b for b in plan.get("blocks", []) if b.get("type") == "diagram"]


def wanted(task):
    return "grill" in (task.get("stages") or {}) or bool(diagrams(task))


def audiences(q):
    to = q.get("to") or []
    return [to] if isinstance(to, str) else list(to)


class ShareCtx(Ctx):
    """Renders IDs as readable names and inlines images, so one file stands on its own."""

    def __init__(self, site, d, t, numbers):
        super().__init__(site, f"{d}/{t}/share/x.html", d, t)
        self.numbers = numbers

    def label(self, raw):
        _, t, item = parse_ref(raw, self.domain, self.task)
        if t == self.task and item in self.numbers:
            return self.numbers[item]
        found = self.site.domains.get(self.domain, {}).get("items", {}).get(self.task, {}).get(item) if t == self.task else None
        if found and found[1].get("cells"):
            first = found[1]["cells"][0]
            first = first.get("text", "") if isinstance(first, dict) else first
            return html.unescape(plain(re.sub(r"<br\s*/?>", " ", str(first)))).strip()
        _, prev = self.resolve(raw)
        if not prev:
            return raw
        title = re.sub(r"<br\s*/?>", " ", str(prev.get("title", "")))
        title = html.unescape(plain(title)).strip()
        if item and title.startswith(item):
            title = title[len(item):].strip(" ·")
        return title.split(" · ")[0] if item and re.fullmatch(r"R\d+", item) else title or raw

    def rich(self, text):
        return REF.sub(lambda m: f'<span class="ref-name">‘{esc(self.label(m.group(1)))}’</span>', str(text if text is not None else ""))

    def frame(self, target):
        path = self.site.docs / target
        return f'srcdoc="{esc(path.read_text())}"' if path.is_file() else ""

    def href(self, target):
        path = self.site.docs / target.split("#")[0]
        kind = mimetypes.guess_type(path.name)[0] or ""
        if kind.startswith("image/") and path.is_file():
            return f"data:{kind};base64,{base64.b64encode(path.read_bytes()).decode()}"
        return "#"


def md_text(ctx, text):
    s = REF.sub(lambda m: f"‘{ctx.label(m.group(1))}’", str(text if text is not None else ""))
    s = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", s, flags=re.S)
    s = re.sub(r"</?(b|strong)>", "**", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def open_items(stage, who):
    out = []
    for r in stage.get("rounds", []):
        for q in r.get("questions", []):
            if who in audiences(q) and needs_answer(q):
                out.append((r, q))
    return out


def decided_items(stage, who):
    return [(r, q) for r in stage.get("rounds", []) for q in r.get("questions", [])
            if who in audiences(q) and not needs_answer(q)]


def context_rows(q, who):
    return [(k, v) for k, v in q.get("context", []) if who == "backend" or k.strip().lower() not in TECH_KEYS]


def options_of(q):
    rec = q.get("recommended", "yes")
    return [(o["label"], o["value"] == rec) for o in (q.get("options") or DEFAULT_OPTIONS)]


def plan_blocks(stage):
    out = []
    for b in stage.get("blocks", []):
        b = copy.deepcopy(b)
        for row in b.get("rows", []) if b.get("type") == "cases" else []:
            for c in row.get("cells", []):
                if isinstance(c, dict):
                    c.pop("enum", None)
        out.append(b)
    return out


# ---------------------------------------------------------------- HTML

def q_html(ctx, n, q, who, word):
    rows = "".join(f'<li><b>{esc(k)}</b><span>{copy_marks(ctx.rich(v))}</span></li>' for k, v in context_rows(q, who))
    ctxl = f'<ul class="q-ctx">{rows}</ul>' if rows else ""
    body = f'<div>{ctx.rich(q["body"])}</div>' if q.get("body") else ""
    opts = "".join(f'<li>{esc(label)}{" <span class=k-rec>추천</span>" if rec else ""}</li>' for label, rec in options_of(q))
    preview = ""
    if who == "plan":
        mock = (q.get("preview") or {}).get(q.get("recommended", "yes"))
        if mock:
            preview = f'<div class="sq-preview"><div class="ui-kind">제안대로라면</div>{mocks_html(ctx, mock if isinstance(mock, list) else [mock])}</div>'
    return (f'<section class="sq"><h3>{word} {n}. {ctx.rich(q.get("title", ""))}</h3>{ctxl}{body}'
            f'<div class="rec-line"><b>제안</b>{ctx.rich(q.get("recommendation", ""))}</div>'
            f'<ol class="sq-opts">{opts}</ol>{preview}</section>')


def to_html(site, d, task, who):
    stage = (task.get("stages") or {}).get("grill") or {}
    title, count_word, word = ASK[who]
    items = open_items(stage, who)
    numbers = {f"{r['id']}-{q['id']}": f"{word} {i}" for i, (r, q) in enumerate(items, 1)}
    ctx = ShareCtx(site, d, task["id"], numbers)
    cards = {f"{r['id']}-{q['id']}": q_html(ctx, i, q, who, word) for i, (r, q) in enumerate(items, 1)}
    parts = []
    if who == "plan":
        homes = question_homes(stage)
        used = set()
        for b in plan_blocks(stage):
            if b.get("type") != "cases":
                continue
            mine = [tag for tag in cards if homes.get(tag) == b.get("id")]
            used.update(mine)
            parts.append((heading(b) if b.get("title") else "") + cases(ctx, b) + "".join(cards[t] for t in mine))
        rest = [cards[t] for t in cards if t not in used]
        if rest:
            parts.append(f'<h2>{"그 밖의 질문" if parts else "질문"}</h2><div>{"".join(rest)}</div>')
    else:
        if cards:
            parts.append(f'<h2>요청할 것</h2><div>{"".join(cards.values())}</div>')
        done = decided_items(stage, who)
        if done:
            lis = "".join(f'<li><b>{ctx.rich(q.get("title", ""))}</b><div>{ctx.rich(q["decision"])}</div></li>' for r, q in done)
            parts.append(f'<h2>이미 정한 것</h2><ul class="sq-done">{lis}</ul>')
    if diagrams(task):
        parts.insert(0, blocks(ctx, {"blocks": diagrams(task)}))
    meta, lead = headline(site, d, task, who, len(items))
    how = f'<p class="note">{esc(lead)}</p>'
    body = (f'<div class="head"><h1>{esc(task.get("title", task["id"]))}</h1><p class="meta">{esc(meta)}</p>{how}</div>'
            f'{"".join(parts) or "<p class=note>지금은 보낼 것이 없어요.</p>"}')
    return ("<!doctype html>\n<html lang=\"ko\"><head><meta charset=\"utf-8\">"
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{esc(task.get('title', ''))} · {esc(AUDIENCES[who])} {title}</title><link rel=\"stylesheet\" href=\"{FONTS}\">"
            f"<style>\n{asset('page.css')}</style>{mock_theme(ctx)}</head>\n"
            f'<body class="share">\n<main class="page">\n{body}\n</main>\n</body></html>\n'), len(items)


# ---------------------------------------------------------------- Markdown

def md_cell(ctx, c):
    if not isinstance(c, dict):
        return md_text(ctx, c)
    bits = [md_text(ctx, c.get("ui", "")), md_text(ctx, c.get("text", ""))]
    for m in c.get("mocks") or []:
        if "modal" in m:
            x = m["modal"]
            bits.append("[모달] " + " / ".join(md_text(ctx, x[k]).replace("\n", " ") for k in ("title", "body") if x.get(k)))
        elif "toast" in m:
            bits.append(f"[스낵바] {md_text(ctx, m['toast'])}")
        elif "banner" in m:
            bits.append(f"[안내] {md_text(ctx, m['banner'].get('body', ''))}")
        elif "shot" in m:
            bits.append("[디자인 캡처]")
    return " · ".join(b for b in bits if b).replace("|", "\\|")


def q_md(ctx, n, q, who, word):
    out = [f"### {word} {n}. {md_text(ctx, q.get('title', ''))}", ""]
    out += [f"- {k}: {md_text(ctx, v)}" for k, v in context_rows(q, who)]
    if q.get("body"):
        out += ["", md_text(ctx, q["body"])]
    out += ["", f"**제안** {md_text(ctx, q.get('recommendation', ''))}", ""]
    out += [f"{i}. {label}{' (추천)' if rec else ''}" for i, (label, rec) in enumerate(options_of(q), 1)]
    return "\n".join(out) + "\n"


def to_md(site, d, task, who):
    stage = (task.get("stages") or {}).get("grill") or {}
    title, count_word, word = ASK[who]
    items = open_items(stage, who)
    numbers = {f"{r['id']}-{q['id']}": f"{word} {i}" for i, (r, q) in enumerate(items, 1)}
    ctx = ShareCtx(site, d, task["id"], numbers)
    cards = {f"{r['id']}-{q['id']}": q_md(ctx, i, q, who, word) for i, (r, q) in enumerate(items, 1)}
    meta, lead = headline(site, d, task, who, len(items))
    out = [f"# {task.get('title', task['id'])}", "", meta, "", lead.replace("이 파일을 받은 ", "이 ")]
    for b in diagrams(task):
        out += ["", f"## {b.get('title') or '흐름도'}", ""] + ([md_text(ctx, b["sub"]), ""] if b.get("sub") else []) + ["그림은 HTML 공유본에서 볼 수 있어요."]
    if who == "plan":
        homes = question_homes(stage)
        used = set()
        for b in plan_blocks(stage):
            if b.get("type") != "cases":
                continue
            out += ["", f"## {b.get('title') or '케이스'}"]
            if b.get("lead"):
                out += ["", md_text(ctx, b["lead"])]
            cols = b.get("columns", [])
            out += ["", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
            for row in b.get("rows", []):
                cells = [md_cell(ctx, c) for c in row.get("cells", [])]
                if "status" in row:
                    cells.append(" · ".join(ch.get("label", "") for ch in row["status"]))
                out.append("| " + " | ".join(cells) + " |")
            mine = [t for t in cards if homes.get(t) == b.get("id")]
            used.update(mine)
            out += [""] + [cards[t] for t in mine]
        rest = [cards[t] for t in cards if t not in used]
        if rest:
            out += ["", "## 그 밖의 질문" if used or plan_blocks(stage) else "## 질문", ""] + rest
    else:
        if cards:
            out += ["", "## 요청할 것", ""] + list(cards.values())
        done = decided_items(stage, who)
        if done:
            out += ["", "## 이미 정한 것", ""] + [f"- **{md_text(ctx, q.get('title', ''))}** — {md_text(ctx, q['decision'])}" for r, q in done]
    return "\n".join(out).rstrip() + "\n", len(items)


def share_path(t, who, fmt):
    return f"{t}/share/{who}.{'html' if fmt == 'html' else 'md'}"


def pages(site, d, t):
    """→ {path relative to docs: text} for every shared copy of a task, plus the menu's numbers."""
    task = site.domains[d]["tasks"][t]
    out, info = {}, {}
    for who in AUDIENCES:
        page, n = to_html(site, d, task, who)
        text, _ = to_md(site, d, task, who)
        out[f"{d}/{share_path(t, who, 'html')}"] = page
        out[f"{d}/{share_path(t, who, 'md')}"] = text
        info[who] = {"n": n, "md": text}
    return out, info


def export(task_file, who, fmt, out=None):
    task_file = Path(task_file).resolve()
    domain_dir = task_file.parent.parent
    site = Site(domain_dir.parent)
    task = site.domains[domain_dir.name]["tasks"][read_json(task_file)["id"]]
    text, n = (to_html if fmt == "html" else to_md)(site, domain_dir.name, task, who)
    path = Path(out) if out else domain_dir / share_path(task["id"], who, fmt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path, n, text
