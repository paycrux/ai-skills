export const STAGES = [
  ["plan", "기획"],
  ["screen", "화면 · SOT 맵"],
  ["grill", "질문"],
  ["tasks", "구현 계획 · 구현"],
  ["verify", "검증"],
  ["done", "완료"],
];
export const STATUSES = ["done", "now", "ask", "wait"];
export const KIND = {
  server: ["Data", "data"],
  format: ["Computed", "comp"],
  calc: ["Computed · 계산", "comp"],
  action: ["Action", "act"],
  pending: ["확인 필요", "pend"],
  out: ["범위 제외", "out"],
  prop: ["Prop", "data"],
  slot: ["Slot", "comp"],
  state: ["State", "act"],
  token: ["Token", "comp"],
};
export const ITEM_ID = /^(S\d+|X\d+|R\d+(-Q\d+)?|P\d+(-[A-Za-z0-9]+)?|[BVD]\d+)$/;
export const REF = /\[\[([^\]\s]+)\]\]/g;

export function grillState(stage) {
  const rounds = (stage && stage.rounds) || [];
  let decided = 0;
  const open = [], revised = [];
  for (const r of rounds) {
    const qs = r.questions || [];
    const isOpen = qs.some((q) => !q.decision);
    const isRevised = !isOpen && qs.some((q) => q.answer && q.answer.by === "user");
    if (isOpen) open.push(r.id);
    else if (isRevised) revised.push(r.id);
    else decided += qs.length;
  }
  let status, summary;
  if (!rounds.length) [status, summary] = ["wait", "질문 없음"];
  else if (open.length || revised.length)
    [status, summary] = ["ask", [...open.map((id) => `${id} 답 대기`), ...revised.map((id) => `${id} 답 수정됨`)].join(" · ")];
  else [status, summary] = ["done", `남은 질문 0 · 결정 ${decided}`];
  return { status, summary, open, revised, decided };
}

export function checklistCount(stage) {
  let total = 0, done = 0;
  for (const b of (stage && stage.blocks) || []) {
    if (b.type !== "checklist") continue;
    for (const it of b.items || []) {
      total += 1;
      if (it.done) done += 1;
    }
  }
  return { total, done };
}

export function stageState(task, key) {
  const stage = task.stages && task.stages[key];
  if (!stage) return { status: "skip", summary: "필요하면 생겨요" };
  if (key === "grill") return grillState(stage);
  const status = STATUSES.includes(stage.status) ? stage.status : "wait";
  let summary = stage.summary || "";
  const c = checklistCount(stage);
  if (c.total) summary = `${summary}${summary ? " · " : ""}체크 ${c.done}/${c.total}`;
  return { status, summary };
}

export function taskState(task) {
  const states = STAGES.map(([k]) => stageState(task, k)).filter((s) => s.status !== "skip");
  if (!states.length) return "wait";
  if (states.some((s) => s.status === "ask")) return "ask";
  if (states.some((s) => s.status === "now")) return "now";
  if (states.every((s) => s.status === "done")) return "done";
  if (states.some((s) => s.status === "done")) return "now";
  return "wait";
}

export function refsIn(text) {
  const out = [];
  if (typeof text !== "string") return out;
  for (const m of text.matchAll(REF)) out.push(m[1]);
  return out;
}

export function walkRefs(node, owner, visit) {
  if (typeof node === "string") {
    for (const r of refsIn(node)) visit(r, owner);
  } else if (Array.isArray(node)) {
    for (const x of node) walkRefs(x, owner, visit);
  } else if (node && typeof node === "object") {
    let here = owner;
    if (typeof node.id === "string" && ITEM_ID.test(node.id)) here = node.id;
    else if (typeof node.id === "string" && /^Q\d+$/.test(node.id) && /^R\d+$/.test(owner || "")) here = `${owner}-${node.id}`;
    for (const [k, v] of Object.entries(node)) if (k !== "id") walkRefs(v, here, visit);
  }
}

export function parseRef(raw, ctx) {
  let domain = ctx.domain, task = null, item = raw;
  const slash = raw.indexOf("/");
  if (slash > 0) {
    domain = raw.slice(0, slash);
    item = raw.slice(slash + 1);
  }
  const hash = item.indexOf("#");
  if (hash > 0) {
    task = item.slice(0, hash);
    item = item.slice(hash + 1);
  } else if (!ITEM_ID.test(item)) {
    task = item;
    item = null;
  } else if (!/^[SX]\d+$/.test(item)) {
    task = ctx.task || null;
  }
  return { domain, task, item };
}

export function refHref(ref) {
  if (ref.task) return `/${ref.domain}/${encodeURIComponent(ref.task)}${ref.item ? "#" + ref.item : ""}`;
  return `/${ref.domain}/${ref.item ? "#" + ref.item : ""}`;
}
