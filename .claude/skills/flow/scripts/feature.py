"""Feature documents: one PRD split into Jira stories, [프론트] issues, worktrees and flow tasks.

    <docs>/features/<id>/feature.json   the feature document (Claude writes it)
    <docs>/features/<id>/prd.md         PRD snapshot, committed; diffed only when the user asks
    <docs>/features/<id>/issues/*.md    description of each [프론트] issue to create
    <docs>/features/<id>/index.html     feature page (generated)

Progress on every row is read from that row's flow task JSON — in this checkout, in the row's
worktree, or from the row's branch — never written by hand.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from model import STAGE_KEYS, git, plain, read_json, stage_skeleton, stage_state, task_state, write_json

FEATURES = "features"
HEAD = re.compile(r"^\s*(#{1,6})\s+(.*)$")
NUM = re.compile(r"^(\d+(?:[-.]\d+)*)\.?\s+(.+)$")
TOKEN = re.compile(r"\d+(?:[-.]\d+)+")
RANGE = re.compile(r"(\d+(?:[-.]\d+)+)\s*(?:~|–|—|부터)\s*(\d+(?:[-.]\d+)+)")
ROW_STATE = {"new": "만들기 전", "wait": "대기", "legacy": "레거시", "plan": "계획", "build": "구현",
             "check": "확인", "done": "완료"}


def feature_dirs(docs):
    root = Path(docs) / FEATURES
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if (p / "feature.json").exists())


def docs_of_feature(path):
    """<docs>/features/<id>/feature.json → <docs>."""
    return Path(path).resolve().parent.parent.parent


# ---------------------------------------------------------------- PRD sections

def clean_heading(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\{[^}]*\}", "", text)
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


def snapshot_sections(path):
    """Numbered headings of a PRD snapshot → [(number, title)] in document order."""
    out, seen = [], set()
    p = Path(path)
    if not p.is_file():
        return out
    for line in p.read_text().splitlines():
        m = HEAD.match(line)
        if not m:
            continue
        n = NUM.match(clean_heading(m.group(2)))
        if not n:
            continue
        num = n.group(1).replace(".", "-")
        if num not in seen:
            seen.add(num)
            out.append((num, n.group(2).strip()))
    return out


def cited(text):
    """Section numbers named in a quote source or a row's `sections` entry."""
    s = plain(str(text or ""))
    out = []
    for a, b in RANGE.findall(s):
        a, b = a.replace(".", "-"), b.replace(".", "-")
        pa, pb = a.rsplit("-", 1), b.rsplit("-", 1)
        if pa[0] == pb[0] and pa[1].isdigit() and pb[1].isdigit() and int(pa[1]) <= int(pb[1]):
            out += [f"{pa[0]}-{i}" for i in range(int(pa[1]), int(pb[1]) + 1)]
    out += [t.replace(".", "-") for t in TOKEN.findall(s)]
    if re.fullmatch(r"\s*\d+\s*", s):
        out.append(s.strip())
    return list(dict.fromkeys(out))


def task_citations(task):
    nums = []
    plan_stage = (task or {}).get("stages", {}).get("plan") or {}
    for b in plan_stage.get("blocks", []):
        if b.get("type") == "quote":
            for it in b.get("items", []):
                nums += cited(it.get("source", ""))
    return nums


def covers(num, section):
    return section == num or section.startswith(num + "-")


# ---------------------------------------------------------------- rows ↔ tasks

def row_key(row):
    return row.get("issue") or row.get("id")


def docs_rel(docs):
    top = git(docs, "rev-parse", "--show-toplevel")
    if not top:
        return Path("docs")
    try:
        return Path(docs).resolve().relative_to(Path(top).resolve())
    except ValueError:
        return Path("docs")


def locate_task(docs, row):
    """→ (task dict or None, where it was read)."""
    tid, dom = row.get("task"), row.get("domain")
    if not tid or not dom:
        return None, ""
    rel = docs_rel(docs) / dom / "tasks" / f"{tid}.json"
    here = Path(docs) / dom / "tasks" / f"{tid}.json"
    wt = Path(row["worktree"]) / rel if row.get("worktree") else None
    for p, label in ((wt, "워크트리"), (here, "이 체크아웃")):
        if p and p.is_file():
            try:
                return json.loads(p.read_text()), label
            except (OSError, ValueError):
                pass
    if row.get("branch"):
        text = git(docs, "show", f"{row['branch']}:{rel.as_posix()}")
        if text:
            try:
                return json.loads(text), f"브랜치 {row['branch']}"
            except ValueError:
                pass
    return None, ""


def task_path(docs, row):
    """Where the row's task JSON lives on disk, preferring its worktree."""
    rel = docs_rel(docs) / row.get("domain", "") / "tasks" / f"{row.get('task')}.json"
    if row.get("worktree") and (Path(row["worktree"]) / rel).is_file():
        return Path(row["worktree"]) / rel
    here = Path(docs) / row.get("domain", "") / "tasks" / f"{row.get('task')}.json"
    return here if here.is_file() else None


def blockers(task):
    n = 0
    for st in (task.get("stages") or {}).values():
        for b in st.get("blocks", []) if isinstance(st, dict) else []:
            for it in b.get("items", []) if b.get("type") == "checklist" else []:
                if not it.get("done") and any(r and r[0] == "blocker" for r in it.get("rows", [])):
                    n += 1
    return n


def row_progress(docs, row):
    """Everything the feature page shows for one row, computed from its task."""
    if row.get("legacy"):
        return {"state": "legacy", "stages": [], "count": None, "blockers": 0, "next": "레거시 계획 — 손으로 끝내거나 flow로 다시 시작", "where": row["legacy"], "task": None}
    task, where = locate_task(docs, row)
    if task is None:
        state = "wait" if row.get("worktree") else "new"
        nxt = "flow.py start" if row.get("approved") else "승인 대기"
        if row.get("worktree"):
            nxt = "워크트리에서 flow 시작"
        return {"state": state, "stages": [], "count": None, "blockers": 0, "next": nxt, "where": "", "task": None}
    stages = task.get("stages") or {}
    states = [(k, stage_state(task, k)) for k in STAGE_KEYS if k in stages]
    total = done = 0
    for k in ("tasks", "verify"):
        for b in (stages.get(k) or {}).get("blocks", []):
            if b.get("type") == "checklist":
                for it in b.get("items", []):
                    total += 1
                    done += bool(it.get("done"))
    st = {k: s["status"] for k, s in states}
    if task_state(task) == "done":
        state = "done"
    elif st.get("tasks") == "done" and st.get("verify") in ("ask", "now"):
        state = "check"
    elif st.get("tasks") in ("now", "done"):
        state = "build"
    else:
        state = "plan"
    nxt = ""
    grill = dict(states).get("grill")
    if grill and grill["status"] == "ask":
        nxt = "질문 답 대기 — " + grill["summary"]
    elif st.get("tasks") == "ask":
        nxt = "구현 계획 검토 대기"
    elif st.get("verify") == "ask":
        nxt = "화면 · 기기 확인 대기"
    elif state == "done":
        nxt = "완료 — PR"
    return {"state": state, "stages": states, "count": (done, total) if total else None,
            "blockers": blockers(task), "next": nxt, "where": where, "task": task}


def section_matrix(docs, feature, progress):
    """PRD sections × rows. → (sections [(num, title, leaf, owners)], missing [(num, owners)])."""
    fdir = Path(docs) / FEATURES / feature["id"]
    sections = []
    for prd in feature.get("prd") or []:
        if prd.get("snapshot"):
            sections += snapshot_sections(fdir / prd["snapshot"])
    nums = [n for n, _ in sections]
    cites = {}
    for row in feature.get("rows", []):
        key = row_key(row)
        own = []
        for s in row.get("sections") or []:
            own += cited(s)
        own += task_citations(progress[key]["task"])
        cites[key] = list(dict.fromkeys(own))
    out = []
    for num, title in sections:
        leaf = not any(o.startswith(num + "-") for o in nums)
        owners = [k for k, cs in cites.items() if any(covers(c, num) for c in cs)]
        out.append((num, title, leaf, owners))
    missing = {}
    for k, cs in cites.items():
        for c in cs:
            if nums and c not in nums and not any(n.startswith(c + "-") for n in nums):
                missing.setdefault(c, []).append(k)
    return out, sorted(missing.items(), key=lambda x: [int(p) for p in x[0].split("-") if p.isdigit()])


# ---------------------------------------------------------------- shell helpers

def run(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:4])} … 실패: {(p.stderr or p.stdout).strip()[:400]}")
    return p.stdout


def common_repo(docs):
    common = git(docs, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return str(Path(common).parent) if common else git(docs, "rev-parse", "--show-toplevel")


def find_path(node):
    if isinstance(node, dict):
        if isinstance(node.get("path"), str) and node["path"].startswith("/"):
            return node["path"]
        for v in node.values():
            hit = find_path(v)
            if hit:
                return hit
    elif isinstance(node, list):
        for v in node:
            hit = find_path(v)
            if hit:
                return hit
    return None


def orca_entry(path):
    data = json.loads(run(["orca", "worktree", "list", "--json"]))
    for w in (data.get("result") or {}).get("worktrees", []):
        if Path(w.get("path", "")).resolve() == Path(path).resolve():
            return w
    return None


# ---------------------------------------------------------------- start

def start(path, only=None, approve=False, dry=False):
    """Create, for every approved row: [프론트] issue, top-level worktree, branch, flow task skeleton.

    No judgment: rows come from the approved feature document, results are written back to it.
    Every finished step is saved at once, so a rerun picks up where a failure stopped.
    """
    path = Path(path).resolve()
    f = read_json(path)
    docs = docs_of_feature(path)
    lines = []
    if not f.get("root"):
        raise RuntimeError("feature.json에 root(다른 개발자와 공유하는 기준 브랜치)가 없어요")
    rows = [r for r in f.get("rows", []) if not only or row_key(r) in only or r.get("id") in only]
    if approve:
        for r in rows:
            r["approved"] = True
    todo = [r for r in rows if r.get("approved") and not r.get("legacy")]
    if not todo:
        return ["승인된 줄이 없어요 — 사용자가 승인한 줄에 \"approved\": true (또는 --approve)"]
    repo = f.get("repo") or common_repo(docs)
    rel = docs_rel(docs)
    has_orca = shutil.which("orca") is not None and not os.environ.get("FLOW_NO_ORCA")
    save = (lambda: None) if dry else (lambda: write_json(path, f))
    save()
    fetched = False
    for row in todo:
        name = row.get("id") or row.get("title")
        # 1. Jira issue
        if not row.get("issue"):
            row["issue"] = existing_issue(row) if not dry else None
            if row["issue"]:
                lines.append(f"{name}: 지라 {row['issue']} 재사용 (같은 제목의 하위 이슈가 이미 있음)")
            elif dry:
                lines.append(f"{name}: 지라 [프론트] 하위 이슈를 만들 예정 — 부모 {row.get('story')}")
                continue
            else:
                row["issue"] = create_issue(f, row, path.parent)
                lines.append(f"{name}: 지라 {row['issue']} 만듦 — 부모 {row.get('story')}")
            save()
        key = row["issue"]
        branch = row.get("branch") or f"feat/{key}"
        # 2. worktree (top-level, from origin/<root>)
        if not row.get("worktree"):
            if dry:
                lines.append(f"{key}: 워크트리 {'orca 최상위' if has_orca else 'git worktree'} + {branch} ← origin/{f['root']} 예정")
                continue
            if not fetched:
                run(["git", "-C", repo, "fetch", "origin", f["root"]])
                fetched = True
            row["worktree"] = create_worktree(repo, key, branch, f["root"], has_orca)
            lines.append(f"{key}: 워크트리 {row['worktree']}" + (" — 최상위 확인" if has_orca else ""))
            save()
        wt = row["worktree"]
        # 3. branch name, no upstream
        current = git(wt, "branch", "--show-current")
        if current and current != branch:
            run(["git", "-C", wt, "branch", "-m", current, branch])
        subprocess.run(["git", "-C", wt, "branch", "--unset-upstream"], capture_output=True)
        row["branch"] = branch
        row.setdefault("base", git(wt, "rev-parse", "--short", "HEAD"))
        save()
        # 4. flow task skeleton
        if not row.get("task"):
            row["task"] = key
        tfile = Path(wt) / rel / row["domain"] / "tasks" / f"{row['task']}.json"
        if not tfile.exists():
            make_task(Path(wt) / rel, f, row, path)
            lines.append(f"{key}: flow 작업 {tfile}")
        save()
    if not lines:
        lines.append("승인된 줄은 모두 만들어져 있어요 — 할 것 없음")
    if not dry:
        moved = settle_home(path, f, todo)
        if moved:
            lines.append(f"기능 문서를 {moved}로 옮겼어요 — 그 브랜치의 다음 커밋에 함께 들어가요")
    return lines


def existing_issue(row):
    out = run(["acli", "jira", "workitem", "search", "--jql", f"parent = {row['story']}",
               "--fields", "key,summary", "--json"], check=False)
    try:
        items = json.loads(out)
    except ValueError:
        return None
    items = items if isinstance(items, list) else items.get("issues") or items.get("workitems") or []
    for it in items:
        summary = (it.get("fields") or {}).get("summary") or it.get("summary")
        if summary == row["title"]:
            return it.get("key")
    return None


def create_issue(f, row, fdir):
    body = fdir / (row.get("issueBody") or "")
    if not row.get("issueBody") or not body.is_file():
        raise RuntimeError(f"{row.get('id')}: issueBody 파일이 없어요 — templates/dev-issue.template.md로 써 두세요")
    jira = f.get("jira") or {}
    project = jira.get("project") or row["story"].split("-")[0]
    adf = Path(tempfile.mkdtemp()) / "issue.adf.json"
    run(["python3", str(Path(__file__).resolve().parents[2] / "_shared" / "jira" / "md_to_adf.py"), str(body), "-o", str(adf)])
    out = run(["acli", "jira", "workitem", "create", "--project", project, "--type", jira.get("issueType", "[개발]"),
               "--parent", row["story"], "--summary", row["title"], "--assignee", "@me",
               "--description-file", str(adf), "--json"])
    m = re.search(r"\b[A-Z][A-Z0-9]+-\d+\b", out)
    if not m:
        raise RuntimeError(f"만든 이슈 키를 읽지 못했어요: {out[:300]}")
    return m.group(0)


def create_worktree(repo, key, branch, root, has_orca):
    if not has_orca:
        wt = str(Path(repo).parent / f"{Path(repo).name}-{key}")
        run(["git", "-C", repo, "worktree", "add", "-b", branch, wt, f"origin/{root}"])
        return wt
    out = run(["orca", "worktree", "create", "--name", key, "--repo", f"path:{repo}", "--base-branch", f"origin/{root}",
               "--branch", branch, "--no-parent", "--json"])
    wt = find_path(json.loads(out))
    if not wt:
        raise RuntimeError(f"orca가 만든 워크트리 경로를 읽지 못했어요: {out[:300]}")
    entry = orca_entry(wt)
    if entry and entry.get("parentWorktreeId"):
        run(["orca", "worktree", "set", "--worktree", f"path:{wt}", "--no-parent", "--json"])
        entry = orca_entry(wt)
        if entry and entry.get("parentWorktreeId"):
            raise RuntimeError(f"{wt}: 상위 워크트리가 남아 있어요 — 중첩된 워크트리에서는 시작하지 않아요")
    return wt


def make_task(wt_docs, f, row, fpath):
    dom = wt_docs / row["domain"]
    if not (dom / "domain.json").exists():
        (dom / "tasks").mkdir(parents=True, exist_ok=True)
        (dom / "images").mkdir(exist_ok=True)
        write_json(dom / "domain.json", {"title": row.get("domainTitle") or row["domain"], "kind": "screens",
                                         "figma": "", "nodes": [], "paths": [], "links": []})
        write_json(dom / "screens.json", {"api": "", "base": "", "flows": [], "screens": []})
    keys = [k.strip() for k in (row.get("stages") or "plan,tasks").split(",") if k.strip()]
    links = [{"label": p.get("label", "기획서"), "url": p["url"]} for p in f.get("prd") or [] if p.get("url")]
    links += row.get("figma") or []
    site = (f.get("jira") or {}).get("site")
    if site:
        links.append({"label": f"지라 {row['issue']}", "url": f"{site.rstrip('/')}/browse/{row['issue']}"})
    task = {"id": row["task"], "title": row.get("taskTitle") or re.sub(r"^\[프론트\]\s*", "", row["title"]),
            "type": row.get("type", "기능 개발"), "branch": row["branch"],
            "feature": {"id": f["id"], "doc": str(fpath)}, "links": links,
            "stages": {k: stage_skeleton(k) for k in STAGE_KEYS if k in keys}}
    (dom / "tasks").mkdir(parents=True, exist_ok=True)
    write_json(dom / "tasks" / f"{row['task']}.json", task)


def settle_home(path, f, rows):
    """The feature document moves once, to the first started row's worktree, and is versioned there."""
    if f.get("home") or not rows or not rows[0].get("worktree"):
        return None
    docs = docs_of_feature(path)
    dest = Path(rows[0]["worktree"]) / docs_rel(docs) / FEATURES / f["id"]
    if dest.resolve() == path.parent.resolve():
        f["home"] = {"branch": rows[0]["branch"], "worktree": rows[0]["worktree"]}
        write_json(path, f)
        return None
    if dest.exists():
        raise RuntimeError(f"{dest}가 이미 있어요 — 어느 쪽이 맞는지 확인해 주세요")
    f["home"] = {"branch": rows[0]["branch"], "worktree": rows[0]["worktree"]}
    write_json(path, f)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path.parent), str(dest))
    new_doc = str(dest / "feature.json")
    for r in f.get("rows", []):
        tp = task_path(docs_of_feature(dest / "feature.json"), r) if r.get("task") else None
        if tp:
            t = read_json(tp)
            if (t.get("feature") or {}).get("doc") != new_doc:
                t["feature"] = {"id": f["id"], "doc": new_doc}
                write_json(tp, t)
    return dest


# ---------------------------------------------------------------- Jira transitions and comment

def feature_of(task):
    doc = (task.get("feature") or {}).get("doc")
    if doc and Path(doc).is_file():
        return Path(doc), read_json(doc)
    return None, None


def row_of(feature, task):
    for r in (feature or {}).get("rows", []):
        if r.get("task") == task.get("id") or r.get("issue") == task.get("id"):
            return r
    return None


def jira_status(key):
    out = run(["acli", "jira", "workitem", "view", key, "--fields", "status", "--json"])
    data = json.loads(out)
    st = (data.get("fields") or {}).get("status") or data.get("status") or {}
    return st.get("name") if isinstance(st, dict) else str(st)


def walk(key, steps, mark, dry=False):
    """Move `key` one transition at a time to the step marked `mark`.

    → (lines, status now, todo). A step marked "manual" (a transition with a precondition such as
    a dev deploy) is never taken; it becomes a 'move by hand' note instead.
    """
    names = [s["status"] for s in steps]
    target = next((i for i, s in enumerate(steps) if s.get("mark") == mark), None)
    if target is None:
        return [f"전환 경로에 \"mark\": \"{mark}\" 단계가 없어요"], None, None
    now = jira_status(key)
    if now not in names:
        return [f"{key}: 지금 상태 '{now}'가 전환 경로에 없어요 — 경로를 다시 읽어 기록해 주세요"], now, None
    lines, todo = [], None
    for s in steps[names.index(now) + 1: target + 1]:
        if s.get("manual"):
            todo = f"{s['status']}" + (f" ({s['via']})" if s.get("via") else "") + " — 사람이 옮길 것"
            lines.append(f"{key}: {todo}")
            break
        if dry:
            lines.append(f"{key}: {now} → {s['status']} 예정")
        else:
            p = subprocess.run(["acli", "jira", "workitem", "transition", "--key", key, "--status", s["status"], "--yes"],
                               capture_output=True, text=True)
            if p.returncode != 0:
                lines.append(f"{key}: {now} → {s['status']} 거절됨 — 전환 경로를 다시 읽어 주세요 ({(p.stderr or p.stdout).strip()[:200]})")
                break
            lines.append(f"{key}: {now} → {s['status']}")
        now = s["status"]
    if not lines:
        lines.append(f"{key}: 이미 {now}")
    return lines, now, todo


def done_comment(task, feature, row, task_file):
    tpl = (Path(__file__).resolve().parent.parent / "templates" / "done-comment.template.md").read_text()
    stages = task.get("stages") or {}
    built = [plain(re.sub(r"\[\[([^\]]+)\]\]", r"\1", c)) for c in (stages.get("tasks") or {}).get("conclusion", [])] or ["(구현 결론 없음)"]
    base = (row or {}).get("base") or (f"origin/{feature['root']}" if feature and feature.get("root") else "")
    log = git(task_file.parent, "log", "--format=%h %s", f"{base}..HEAD") if base else ""
    commits = [f"- `{ln.split(' ', 1)[0]}` {ln.split(' ', 1)[1] if ' ' in ln else ''}" for ln in log.splitlines()] or ["- (커밋 없음)"]
    open_q = [f"- {q['text']}" for q in (feature or {}).get("questions", []) if q.get("row") in (task["id"], (row or {}).get("id"))]
    for r in (stages.get("grill") or {}).get("rounds", []):
        for q in r.get("questions", []):
            if not q.get("decision"):
                open_q.append(f"- {plain(q.get('title', ''))}")
    checked = sum(1 for b in (stages.get("verify") or {}).get("blocks", []) if b.get("type") == "checklist"
                  for it in b.get("items", []) if it.get("done"))
    text = (tpl.replace("{이슈 키}", task["id"]).replace("{제목}", task.get("title", ""))
            .replace("- {화면·기능 단위 한 줄}", "\n".join(f"- {b}" for b in built))
            .replace("{브랜치}", task.get("branch", ""))
            .replace("- `{해시}` {커밋 제목}", "\n".join(commits))
            .replace("- {질문 — 구현에는 영향 없음}", "\n".join(open_q) or "- 없음")
            .replace("{N}", str(checked)).replace("{YYYY-MM-DD}", date.today().isoformat()))
    return text


def jira_step(task_file, mark, dry=False):
    task_file = Path(task_file).resolve()
    task = read_json(task_file)
    fpath, feature = feature_of(task)
    row = row_of(feature, task)
    key = (row or {}).get("issue") or task["id"]
    if not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", key):
        return [f"{task['id']}: 지라 키가 아니에요 — 지라 전환은 건너뜀"]
    steps = ((feature or {}).get("jira") or {}).get("path") or (task.get("jira") or {}).get("path")
    if not steps:
        return [f"{key}: 지라 전환 경로가 없어요 — Atlassian MCP getTransitionsForJiraIssue(includeUnavailableTransitions)로 "
                "읽어 feature.json(없으면 task) jira.path에 기록해요"]
    lines = []
    if mark == "done":
        body = done_comment(task, feature, row, task_file)
        if dry:
            lines.append("완료 댓글 (보내지 않음):\n" + body)
        else:
            tmp = Path(tempfile.mkdtemp()) / f"{key}-done.txt"
            tmp.write_text(body)
            run(["acli", "jira", "workitem", "comment", "create", "--key", key, "--body-file", str(tmp)])
            lines.append(f"{key}: 완료 댓글을 달았어요")
    moved, now, todo = walk(key, steps, mark, dry)
    lines += moved
    if row is not None and not dry:
        row["jira"] = {"status": now, **({"todo": todo} if todo else {})}
        write_json(fpath, feature)
    elif not dry and todo:
        task.setdefault("jira", {})["todo"] = todo
        write_json(task_file, task)
    return lines
