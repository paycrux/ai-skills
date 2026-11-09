"""Which stages this person works with: the core catalog, the team's required stages, and the
personal plugins layered on top.

  core      model.CORE_STAGES — fixed by the skill
  team      <docs>/flow.config.json  "workflow": {"required": [...], "labels": {...}}   (committed)
  personal  $FLOW_HOME/config.json   {"plugins": ["<id>", ...]}                          (not committed)
            $FLOW_HOME/plugins/<id>/plugin.json

A personal plugin may take optional stages out of the person's workflow, rename any stage, add its own
stages and attach to a core stage to collect more data there, but never turn off a stage the team
requires. A stage out of the workflow is still created and filled; only its page and stops go. $FLOW_HOME defaults to $XDG_CONFIG_HOME/flow or ~/.config/flow.
"""
import json
import os
import re
from pathlib import Path

import model

CONFIG = "flow.config.json"
PLUGIN_KEYS = {"id", "stages", "custom", "attach", "style"}
CUSTOM_KEYS = {"key", "title", "after", "instructions", "check"}
ATTACH_KEYS = {"stage", "title", "instructions", "fields", "check"}
SHORT_KEY = re.compile(r"[a-z][a-z0-9-]*")


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


def _stage_list(value, label, known, problems):
    if not isinstance(value, list):
        problems.append(f"{label}: 단계 키 목록이어야 해요")
        return []
    bad = [k for k in value if k not in known]
    if bad:
        problems.append(f"{label}: 없는 단계 {', '.join(map(str, bad))} — {' · '.join(known)} 중에서")
    return [k for k in value if k in known]


def _labels(value, label, known, problems):
    if not isinstance(value, dict):
        problems.append(f"{label}: {{단계 키: 이름}} 객체여야 해요")
        return {}
    bad = [k for k in value if k not in known]
    if bad:
        problems.append(f"{label}: 없는 단계 {', '.join(bad)}")
    return {k: str(v) for k, v in value.items() if k in known and v}


def team(docs, problems):
    """<docs>/flow.config.json "workflow" → (required, labels)."""
    path = Path(docs) / CONFIG if docs else None
    if not path or not path.exists():
        return [], {}
    raw = _read(path, CONFIG, problems)
    wf = (raw or {}).get("workflow")
    if not wf:
        return [], {}
    if not isinstance(wf, dict):
        problems.append(f"{CONFIG}: workflow는 객체예요 — required · labels")
        return [], {}
    unknown = sorted(set(wf) - {"required", "labels"})
    if unknown:
        problems.append(f"{CONFIG}: workflow의 모르는 키 {', '.join(unknown)} — required · labels만 읽어요")
    required = _stage_list(wf.get("required", []), f"{CONFIG} workflow.required", model.CORE_KEYS, problems)
    labels = _labels(wf.get("labels", {}), f"{CONFIG} workflow.labels", model.CORE_KEYS, problems)
    return required, labels


def plugin(pid, problems):
    """$FLOW_HOME/plugins/<id>/plugin.json → normalized plugin, or None."""
    folder = home() / "plugins" / pid
    label = f"플러그인 {pid}"
    if not (folder / "plugin.json").is_file():
        problems.append(f"{label}: {folder / 'plugin.json'}이 없어요 — flow.py plugin new {pid}")
        return None
    raw = _read(folder / "plugin.json", label, problems)
    if raw is None:
        return None
    unknown = sorted(set(raw) - PLUGIN_KEYS)
    if unknown:
        problems.append(f"{label}: 모르는 키 {', '.join(unknown)} — {' · '.join(sorted(PLUGIN_KEYS))}만 읽어요")
    if raw.get("id", pid) != pid:
        problems.append(f"{label}: id({raw.get('id')})가 폴더 이름과 달라요")
    out = {"id": pid, "dir": folder, "use": None, "labels": {}, "custom": [], "attach": [], "style": ""}
    for c in raw.get("custom") or []:
        if not isinstance(c, dict):
            problems.append(f"{label} custom: 단계마다 객체여야 해요")
            continue
        short = str(c.get("key", ""))
        if not SHORT_KEY.fullmatch(short):
            problems.append(f"{label} custom: key '{short}'는 영어 소문자 · 숫자 · -로 (예: perf)")
            continue
        key = f"{pid}:{short}"
        bad = sorted(set(c) - CUSTOM_KEYS)
        if bad:
            problems.append(f"{label} custom {short}: 모르는 키 {', '.join(bad)} — {' · '.join(sorted(CUSTOM_KEYS))}")
        after = c.get("after", "done")
        known_after = model.CORE_KEYS + [x["key"] for x in out["custom"]]
        if after not in known_after:
            problems.append(f"{label} custom {short}: after '{after}'는 {' · '.join(known_after)} 중 하나")
            after = "done"
        if not c.get("title"):
            problems.append(f"{label} custom {short}: title이 없어요")
        ins = c.get("instructions")
        if not ins:
            problems.append(f"{label} custom {short}: instructions(이 단계에서 Claude가 따를 절차 문서)가 없어요")
        elif not (folder / ins).is_file():
            problems.append(f"{label} custom {short}: instructions 파일이 없어요 ({folder / ins})")
        out["custom"].append({"key": key, "title": str(c.get("title") or short), "after": after, "plugin": pid,
                              "instructions": str(folder / ins) if ins else "", "check": c.get("check") or "",
                              "dir": str(folder)})
    for a in raw.get("attach") or []:
        if not isinstance(a, dict):
            problems.append(f"{label} attach: 붙일 단계마다 객체여야 해요")
            continue
        stage = a.get("stage")
        if stage not in model.CORE_KEYS:
            problems.append(f"{label} attach: stage '{stage}'는 {' · '.join(model.CORE_KEYS)} 중 하나")
            continue
        bad = sorted(set(a) - ATTACH_KEYS)
        if bad:
            problems.append(f"{label} attach {stage}: 모르는 키 {', '.join(bad)} — {' · '.join(sorted(ATTACH_KEYS))}")
        fields = a.get("fields") or []
        if not isinstance(fields, list) or not all(isinstance(x, str) and x for x in fields):
            problems.append(f"{label} attach {stage}: fields는 모을 값 이름의 목록이에요")
            fields = []
        if set(fields) & {"unknown", "inferred"}:
            problems.append(f"{label} attach {stage}: unknown · inferred는 flow가 쓰는 이름이라 fields에 못 써요")
        ins = a.get("instructions")
        if not ins:
            problems.append(f"{label} attach {stage}: instructions(이 단계에서 Claude가 더 할 일)가 없어요")
        elif not (folder / ins).is_file():
            problems.append(f"{label} attach {stage}: instructions 파일이 없어요 ({folder / ins})")
        out["attach"].append({"stage": stage, "plugin": pid, "title": str(a.get("title") or pid),
                              "instructions": str(folder / ins) if ins else "", "fields": fields,
                              "check": a.get("check") or "", "dir": str(folder)})
    known = model.CORE_KEYS + [c["key"] for c in out["custom"]]
    st = raw.get("stages") or {}
    if not isinstance(st, dict):
        problems.append(f"{label}: stages는 객체예요 — use · labels")
        st = {}
    bad = sorted(set(st) - {"use", "labels"})
    if bad:
        problems.append(f"{label} stages: 모르는 키 {', '.join(bad)} — use · labels")
    if "use" in st:
        out["use"] = _stage_list(st["use"], f"{label} stages.use", model.CORE_KEYS, problems)
    out["labels"] = _labels(st.get("labels", {}), f"{label} stages.labels", known, problems)
    if raw.get("style"):
        css = folder / raw["style"]
        if css.is_file():
            out["style"] = css.read_text()
        else:
            problems.append(f"{label}: style 파일이 없어요 ({css})")
    return out


def personal(problems):
    """$FLOW_HOME/config.json → [plugin]."""
    path = home() / "config.json"
    if not path.exists():
        return []
    raw = _read(path, str(path), problems)
    if raw is None:
        return []
    unknown = sorted(set(raw) - {"plugins"})
    if unknown:
        problems.append(f"{path}: 모르는 키 {', '.join(unknown)} — plugins만 읽어요")
    ids = raw.get("plugins") or []
    if not isinstance(ids, list):
        problems.append(f"{path}: plugins는 플러그인 id 목록이에요")
        return []
    return [p for p in (plugin(str(i), problems) for i in ids) if p]


def load(docs=None):
    """→ the effective workflow, with every problem found on the way."""
    problems = []
    required, team_labels = team(docs, problems)
    plugins = personal(problems)
    source = {k: "코어" for k in model.CORE_KEYS}
    for k in required:
        source[k] = "팀 필수"
    uses = [p for p in plugins if p["use"] is not None]
    if uses:
        chosen = set().union(*(set(p["use"]) for p in uses))
        for p in uses:
            for k in required:
                if k not in p["use"]:
                    problems.append(f"플러그인 {p['id']}: 팀 필수 단계 {k}를 뺐어요 — 팀 필수는 끌 수 없어서 켜 둔 채로 써요")
    else:
        chosen = set(model.CORE_KEYS)
    custom = [c for p in plugins for c in p["custom"]]
    seen = {}
    for c in custom:
        source[c["key"]] = f"플러그인 {c['plugin']}"
        seen[c["key"]] = seen.get(c["key"], 0) + 1
    dup = sorted(k for k, n in seen.items() if n > 1)
    if dup:
        problems.append(f"같은 단계를 두 번 만들었어요: {', '.join(dup)}")
    enabled = [k for k in model.CORE_KEYS if k in chosen or k in required] + list(dict.fromkeys(c["key"] for c in custom))
    labels, label_from = dict(team_labels), {k: "팀" for k in team_labels}
    for p in plugins:
        for k, v in p["labels"].items():
            if label_from.get(k, "").startswith("플러그인") and labels.get(k) != v:
                problems.append(f"단계 {k}의 이름을 {label_from[k]}와 플러그인 {p['id']}가 다르게 정했어요 — 뒤의 것을 써요")
            labels[k] = v
            label_from[k] = f"플러그인 {p['id']}"
    return {"docs": str(docs) if docs else "", "required": required, "enabled": enabled, "labels": labels,
            "label_from": label_from, "source": source, "custom": custom, "plugins": plugins,
            "attach": [a for p in plugins for a in p["attach"]],
            "styles": [p["style"] for p in plugins if p["style"]], "problems": problems, "home": str(home())}


_current = {}


def use(docs=None):
    """Load the workflow for docs and apply it to model's live catalog. Cached per docs folder."""
    key = (str(Path(docs).resolve()) if docs else "", str(home()))
    if _current.get("key") != key:
        wf = load(docs)
        model.apply_workflow(wf["custom"], wf["labels"], wf["enabled"])
        _current.update(key=key, wf=wf)
    return _current["wf"]


def current():
    return _current.get("wf") or use(None)
