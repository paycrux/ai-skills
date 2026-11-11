"""Which stages this person works with: the core catalog, every stage of it required, and the person's
own extensions on top.

  core      model.CORE_STAGES — fixed by the skill, all required
  team      <docs>/flow.config.json  "workflow": {"labels": {...}}                          (committed)
  personal  $FLOW_HOME/config.json   {"id", "labels", "custom", "attach", "commands", "style"} (not committed)

The personal file only extends: it adds the person's own stages, attaches more data to a core stage, adds
commands of their own (an export, a sync to a notes app), renames stages and restyles their own pages.
It never removes a core stage. Whatever it writes into a task carries its own title, so a teammate
without the file reads and edits the same task. $FLOW_HOME defaults to $XDG_CONFIG_HOME/flow or ~/.config/flow.
"""
import json
import os
import re
from pathlib import Path

import model

CONFIG = "flow.config.json"
PERSONAL_KEYS = {"id", "labels", "custom", "attach", "commands", "style"}
CUSTOM_KEYS = {"key", "title", "after", "instructions", "check"}
ATTACH_KEYS = {"stage", "title", "instructions", "fields", "check"}
COMMAND_KEYS = {"name", "title", "run", "on"}
COMMAND_ON = ("ask", "build")
# Names flow itself writes inside ext.<id>, so an attachment cannot collect a field under them.
EXT_RESERVED = {"title", "unknown", "inferred"}
SHORT_KEY = re.compile(r"[a-z][a-z0-9-]*")
REMOVED = "기본 단계는 모두 필수라서 읽지 않아요 — 지워도 돼요"


def home():
    if os.environ.get("FLOW_HOME"):
        return Path(os.environ["FLOW_HOME"]).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "flow"


def docs_for(path):
    """Any path inside a docs tree (docs, domain, task JSON, page) → the docs folder, or None."""
    if not path:
        return None
    p = Path(path).resolve()
    for d in [p, *p.parents]:
        if (d / "domain.json").exists():
            return d.parent
        if d.is_dir() and ((d / CONFIG).exists() or any((c / "domain.json").exists() for c in d.iterdir() if c.is_dir())):
            return d
    return None


def _read(path, label, problems):
    try:
        data = json.loads(Path(path).read_text())
    except ValueError as e:
        problems.append(f"{label}: JSON을 읽지 못했어요 ({e})")
        return None
    if not isinstance(data, dict):
        problems.append(f"{label}: JSON 객체여야 해요")
        return None
    return data


def _labels(value, label, problems, known=None):
    known = known or model.CORE_KEYS
    if not isinstance(value, dict):
        problems.append(f"{label}: {{단계 키: 이름}} 객체여야 해요")
        return {}
    bad = [k for k in value if k not in known]
    if bad:
        problems.append(f"{label}: 없는 단계 {', '.join(bad)}")
    return {k: str(v) for k, v in value.items() if k in known and v}


def team(docs, problems):
    """<docs>/flow.config.json "workflow" → labels."""
    path = Path(docs) / CONFIG if docs else None
    if not path or not path.exists():
        return {}
    raw = _read(path, CONFIG, problems)
    wf = (raw or {}).get("workflow")
    if not wf:
        return {}
    if not isinstance(wf, dict):
        problems.append(f"{CONFIG}: workflow는 객체예요 — labels")
        return {}
    if "required" in wf:
        problems.append(f"{CONFIG}: workflow.required는 {REMOVED}")
    unknown = sorted(set(wf) - {"required", "labels"})
    if unknown:
        problems.append(f"{CONFIG}: workflow의 모르는 키 {', '.join(unknown)} — labels만 읽어요")
    return _labels(wf.get("labels", {}), f"{CONFIG} workflow.labels", problems)


def _custom(raw, pid, folder, problems):
    out = []
    for c in raw.get("custom") or []:
        if not isinstance(c, dict):
            problems.append("custom: 단계마다 객체여야 해요")
            continue
        short = str(c.get("key", ""))
        if not SHORT_KEY.fullmatch(short):
            problems.append(f"custom: key '{short}'는 영어 소문자 · 숫자 · -로 (예: perf)")
            continue
        bad = sorted(set(c) - CUSTOM_KEYS)
        if bad:
            problems.append(f"custom {short}: 모르는 키 {', '.join(bad)} — {' · '.join(sorted(CUSTOM_KEYS))}")
        after = c.get("after", "done")
        known_after = model.CORE_KEYS + [x["key"] for x in out]
        if after not in known_after:
            problems.append(f"custom {short}: after '{after}'는 {' · '.join(known_after)} 중 하나")
            after = "done"
        if not c.get("title"):
            problems.append(f"custom {short}: title이 없어요")
        ins = c.get("instructions")
        if not ins:
            problems.append(f"custom {short}: instructions(이 단계에서 Claude가 따를 절차 문서)가 없어요")
        elif not (folder / ins).is_file():
            problems.append(f"custom {short}: instructions 파일이 없어요 ({folder / ins})")
        out.append({"key": f"{pid}:{short}", "title": str(c.get("title") or short), "after": after, "plugin": pid,
                    "instructions": str(folder / ins) if ins else "", "check": c.get("check") or "", "dir": str(folder)})
    return out


def _attach(raw, pid, folder, problems):
    out = []
    for a in raw.get("attach") or []:
        if not isinstance(a, dict):
            problems.append("attach: 붙일 단계마다 객체여야 해요")
            continue
        stage = a.get("stage")
        if stage not in model.CORE_KEYS:
            problems.append(f"attach: stage '{stage}'는 {' · '.join(model.CORE_KEYS)} 중 하나")
            continue
        bad = sorted(set(a) - ATTACH_KEYS)
        if bad:
            problems.append(f"attach {stage}: 모르는 키 {', '.join(bad)} — {' · '.join(sorted(ATTACH_KEYS))}")
        fields = a.get("fields") or []
        if not isinstance(fields, list) or not all(isinstance(x, str) and x for x in fields):
            problems.append(f"attach {stage}: fields는 모을 값 이름의 목록이에요")
            fields = []
        if set(fields) & EXT_RESERVED:
            problems.append(f"attach {stage}: {' · '.join(sorted(EXT_RESERVED))}는 flow가 쓰는 이름이라 fields에 못 써요")
        ins = a.get("instructions")
        if not ins:
            problems.append(f"attach {stage}: instructions(이 단계에서 Claude가 더 할 일)가 없어요")
        elif not (folder / ins).is_file():
            problems.append(f"attach {stage}: instructions 파일이 없어요 ({folder / ins})")
        out.append({"stage": stage, "plugin": pid, "title": str(a.get("title") or stage),
                    "instructions": str(folder / ins) if ins else "", "fields": fields,
                    "check": a.get("check") or "", "dir": str(folder)})
    return out


def _commands(raw, folder, problems):
    out = []
    for c in raw.get("commands") or []:
        if not isinstance(c, dict):
            problems.append("commands: 명령마다 객체여야 해요")
            continue
        name = str(c.get("name", ""))
        if not SHORT_KEY.fullmatch(name):
            problems.append(f"commands: name '{name}'는 영어 소문자 · 숫자 · -로 (예: obsidian)")
            continue
        bad = sorted(set(c) - COMMAND_KEYS)
        if bad:
            problems.append(f"commands {name}: 모르는 키 {', '.join(bad)} — {' · '.join(sorted(COMMAND_KEYS))}")
        if not c.get("run"):
            problems.append(f"commands {name}: run(실행할 셸 명령)이 없어요")
            continue
        on = c.get("on", "ask")
        if on not in COMMAND_ON:
            problems.append(f"commands {name}: on은 {' · '.join(COMMAND_ON)} 중 하나 — ask는 부를 때만, build는 build 뒤마다")
            on = "ask"
        out.append({"name": name, "title": str(c.get("title") or name), "run": str(c["run"]), "on": on, "dir": str(folder)})
    names = [c["name"] for c in out]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        problems.append(f"commands: 같은 이름이 두 번 있어요 — {', '.join(dup)}")
    return out


def personal(problems):
    """$FLOW_HOME/config.json → {"id", "labels", "custom", "attach", "commands", "style"}."""
    out = {"id": "", "labels": {}, "custom": [], "attach": [], "commands": [], "style": ""}
    folder = home()
    path = folder / "config.json"
    if not path.exists():
        return out
    raw = _read(path, str(path), problems)
    if raw is None:
        return out
    if "off" in raw:
        problems.append(f"{path}: off는 {REMOVED}")
    unknown = sorted(set(raw) - PERSONAL_KEYS - {"off"})
    if unknown:
        problems.append(f"{path}: 모르는 키 {', '.join(unknown)} — {' · '.join(sorted(PERSONAL_KEYS))}만 읽어요")
    pid = str(raw.get("id") or "")
    if (raw.get("custom") or raw.get("attach")) and not SHORT_KEY.fullmatch(pid):
        problems.append(f"{path}: custom · attach를 쓰려면 id가 있어야 해요 — 영어 소문자 · 숫자 · - (예: hyunsu). "
                        "내 단계 키(<id>:<key>)와 붙인 값(ext.<id>)의 이름이 돼요")
        pid = pid if SHORT_KEY.fullmatch(pid) else "me"
    out["id"] = pid
    out["custom"] = _custom(raw, pid, folder, problems)
    out["attach"] = _attach(raw, pid, folder, problems)
    out["commands"] = _commands(raw, folder, problems)
    out["labels"] = _labels(raw.get("labels", {}), f"{path} labels", problems,
                            model.CORE_KEYS + [c["key"] for c in out["custom"]])
    if raw.get("style"):
        css = folder / raw["style"]
        if css.is_file():
            out["style"] = css.read_text()
        else:
            problems.append(f"{path}: style 파일이 없어요 ({css})")
    return out


def load(docs=None):
    """→ the effective workflow, with every problem found on the way."""
    problems = []
    team_labels = team(docs, problems)
    mine = personal(problems)
    source = {k: "코어 · 필수" for k in model.CORE_KEYS}
    for c in mine["custom"]:
        source[c["key"]] = "내 단계"
    keys = [c["key"] for c in mine["custom"]]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        problems.append(f"같은 단계를 두 번 만들었어요: {', '.join(dup)}")
    labels, label_from = dict(team_labels), {k: "팀" for k in team_labels}
    for k, v in mine["labels"].items():
        labels[k] = v
        label_from[k] = "개인"
    return {"docs": str(docs) if docs else "", "labels": labels, "label_from": label_from, "source": source,
            "custom": mine["custom"], "attach": mine["attach"], "commands": mine["commands"],
            "style": mine["style"], "problems": problems, "home": str(home())}


_current = {}


def use(docs=None):
    """Load the workflow for docs and apply it to model's live catalog. Cached per docs folder."""
    key = (str(Path(docs).resolve()) if docs else "", str(home()))
    if _current.get("key") != key:
        wf = load(docs)
        model.apply_workflow(wf["custom"], wf["labels"])
        _current.update(key=key, wf=wf)
    return _current["wf"]


def current():
    return _current.get("wf") or use(None)
