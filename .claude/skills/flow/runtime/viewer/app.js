import { STAGES, KIND, REF, grillState, stageState, taskState, walkRefs, parseRef, refHref } from "/_flow/model.js";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const nav = $("#nav"), page = $("#page"), savebar = $("#savebar"), peek = $("#peek"), toastEl = $("#toast");

const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const STATE_LABEL = { done: "완료", now: "진행 중", ask: "질문 · 결정 대기", wait: "시작 전", skip: "건너뜀" };

let tree = null;
const domains = new Map();
const dirty = new Map();
let ctx = { domain: null, task: null };
let lastVersion = null;

function toast(text, err) {
  toastEl.textContent = text;
  toastEl.className = "toast show" + (err ? " err" : "");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => (toastEl.className = "toast"), 3200);
}

async function getJson(url, opts) {
  const r = await fetch(url, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(body.error || r.statusText), { status: r.status, body });
  return body;
}

async function loadDomain(id, force) {
  if (!force && domains.has(id)) return domains.get(id);
  const d = await getJson(`/api/domain/${encodeURIComponent(id)}`);
  for (const e of [d.domain, d.screens, ...d.tasks].filter(Boolean)) e.original = same(e.data);
  domains.set(id, d);
  return d;
}

const draftKey = (p) => `flow-draft:${tree?.repo}:${p}`;

function fileEntry(d, path) {
  if (d.domain.path === path) return d.domain;
  if (d.screens && d.screens.path === path) return d.screens;
  return d.tasks.find((t) => t.path === path);
}

function clean(v) {
  if (Array.isArray(v)) return v.map(clean);
  if (v && typeof v === "object") {
    const out = {};
    for (const [k, x] of Object.entries(v)) {
      if (k === "by") continue;
      const c = clean(x);
      if (c === "" || c === undefined || (c && typeof c === "object" && !Array.isArray(c) && !Object.keys(c).length)) continue;
      out[k] = c;
    }
    return out;
  }
  return v;
}

const same = (data) => JSON.stringify(clean(data));

function markDirty(entry) {
  if (entry.original !== undefined && same(entry.data) === entry.original) {
    dirty.delete(entry.path);
    try { localStorage.removeItem(draftKey(entry.path)); } catch {}
    renderSavebar();
    const y = window.scrollY;
    render().then(() => window.scrollTo(0, y));
    return;
  }
  dirty.set(entry.path, entry);
  try { localStorage.setItem(draftKey(entry.path), JSON.stringify({ hash: entry.hash, data: entry.data })); } catch {}
  renderSavebar();
}

function restoreDrafts(d) {
  const notes = [];
  for (const entry of [d.domain, d.screens, ...d.tasks].filter(Boolean)) {
    let draft = null;
    const held = dirty.get(entry.path);
    if (held) {
      entry.data = held.data;
      entry.hash = held.hash;
      dirty.set(entry.path, entry);
      continue;
    }
    try { draft = JSON.parse(localStorage.getItem(draftKey(entry.path)) || "null"); } catch {}
    if (!draft) continue;
    if (draft.hash === entry.hash && same(draft.data) === entry.original) {
      try { localStorage.removeItem(draftKey(entry.path)); } catch {}
      continue;
    }
    if (draft.hash === entry.hash) {
      entry.data = draft.data;
      dirty.set(entry.path, entry);
      notes.push({ path: entry.path, kind: "restored" });
    } else {
      notes.push({ path: entry.path, kind: "stale", draft });
    }
  }
  return notes;
}

// ---------------------------------------------------------------- rich text and references

function rich(text) {
  return String(text ?? "").replace(REF, (_, raw) => {
    const ref = parseRef(raw, ctx);
    return `<a class="ref" data-raw="${esc(raw)}" href="${esc(refHref(ref))}">${esc(raw)}</a>`;
  });
}

function unrich(el) {
  const clone = el.cloneNode(true);
  $$("a.ref", clone).forEach((a) => a.replaceWith(`[[${a.dataset.raw}]]`));
  return clone.innerHTML.trim();
}

function findItem(d, ref) {
  if (!ref.item) {
    const t = d.tasks.find((x) => x.data.id === ref.task);
    return t ? { where: `${d.id} · 작업`, title: `${t.data.id} ${t.data.title}`, body: STATE_LABEL[taskState(t.data)] } : null;
  }
  if (/^S\d+$/.test(ref.item) || /^X\d+$/.test(ref.item)) {
    for (const s of d.screens?.data.screens || []) {
      const m = (s.markers || []).find((x) => x.id === ref.item);
      if (m) return { where: `${d.id} · ${s.title}`, title: `${m.id} ${m.title}`, body: `<span class="k ${KIND[m.kind]?.[1]}">${KIND[m.kind]?.[0]}</span> ${m.field && m.field !== "—" ? m.field + " · " : ""}${m.rule || ""}` };
      const x = (s.offscreen || []).find((o) => o.id === ref.item);
      if (x) return { where: `${d.id} · ${s.title} · 화면 밖`, title: `${x.id} ${x.state}`, body: `${x.when} → ${x.shows}` };
    }
    return null;
  }
  const t = d.tasks.find((x) => x.data.id === ref.task);
  if (!t) return null;
  let hit = null;
  const visit = (node, stageKey) => {
    if (hit || !node || typeof node !== "object") return;
    if (Array.isArray(node)) return node.forEach((n) => visit(n, stageKey));
    if (node.id === ref.item) {
      hit = { node, stageKey };
      return;
    }
    Object.values(node).forEach((v) => visit(v, stageKey));
  };
  for (const [k, st] of Object.entries(t.data.stages || {})) visit(st, k);
  const r = /^R\d+-Q\d+$/.test(ref.item) ? ref.item.split("-") : null;
  if (!hit && r) {
    const round = t.data.stages?.grill?.rounds?.find((x) => x.id === r[0]);
    const q = round?.questions?.find((x) => x.id === r[1]);
    if (q) hit = { node: q, stageKey: "grill" };
  }
  if (!hit) return null;
  const n = hit.node;
  const where = `${t.data.id} · ${STAGES.find(([k]) => k === hit.stageKey)?.[1] || ""}`;
  if (n.questions) return { where, title: `${n.id} · ${n.from || ""}`, body: n.questions.map((q) => esc(q.title)).join(" · ") };
  if (n.recommendation !== undefined) return { where, title: `${ref.item} ${n.title}`, body: n.decision || "답을 기다려요" };
  if (n.items) return { where, title: n.title, body: n.items.map((i) => `${i.done ? "✓" : "○"} ${i.title}`).join("<br>") };
  return { where, title: `${n.id} ${n.title || ""}`, body: (n.rows || []).map(([a, b]) => `${a}: ${b}`).join("<br>") };
}

async function resolve(raw) {
  const ref = parseRef(raw, ctx);
  try {
    const d = await loadDomain(ref.domain);
    return { ref, item: findItem(d, ref) };
  } catch {
    return { ref, item: null };
  }
}

function markBroken(root) {
  $$("a.ref[data-raw]", root).forEach(async (a) => {
    const { item } = await resolve(a.dataset.raw);
    if (!item) {
      a.classList.add("broken");
      a.title = "찾을 수 없는 참조";
    }
  });
}

document.addEventListener("mouseover", async (e) => {
  const a = e.target.closest?.("a.ref[data-raw]");
  if (!a) return;
  const { item } = await resolve(a.dataset.raw);
  if (!a.matches(":hover")) return;
  peek.innerHTML = item ? `<div class="where">${esc(item.where)}</div><b>${rich(item.title)}</b><div>${rich(item.body || "")}</div>` : `<b>${esc(a.dataset.raw)}</b>찾을 수 없는 참조예요`;
  const r = a.getBoundingClientRect();
  peek.hidden = false;
  const w = peek.offsetWidth, h = peek.offsetHeight;
  peek.style.left = Math.min(window.innerWidth - w - 12, Math.max(12, r.left)) + "px";
  peek.style.top = (r.bottom + h + 12 > window.innerHeight ? r.top - h - 8 : r.bottom + 8) + "px";
});
document.addEventListener("mouseout", (e) => {
  if (e.target.closest?.("a.ref")) peek.hidden = true;
});

// ---------------------------------------------------------------- routing

function route() {
  const parts = decodeURIComponent(location.pathname).split("/").filter(Boolean);
  if (parts[0] === "legacy") return { view: "legacy", path: parts.slice(1).join("/") };
  if (!parts.length) return { view: "home" };
  if (parts.length === 1) return { view: "domain", domain: parts[0] };
  return { view: "task", domain: parts[0], task: parts[1] };
}

function go(href) {
  history.replaceState({ y: window.scrollY }, "");
  history.pushState({ y: 0 }, "", href);
  render().then(() => scrollToHash(true));
}

document.addEventListener("click", (e) => {
  const a = e.target.closest?.("a[href]");
  if (!a || a.target || e.metaKey || e.ctrlKey || e.shiftKey) return;
  const url = new URL(a.href, location.href);
  if (url.origin !== location.origin || url.pathname.startsWith("/files/") || url.pathname.startsWith("/_flow/")) return;
  e.preventDefault();
  peek.hidden = true;
  if (url.pathname === location.pathname && url.hash) {
    history.replaceState({ y: window.scrollY }, "");
    history.pushState({ y: 0 }, "", url.href);
    scrollToHash(true);
  } else go(url.pathname + url.hash);
});

window.addEventListener("popstate", (e) => {
  render().then(() => {
    if (e.state && typeof e.state.y === "number" && e.state.y > 0) window.scrollTo(0, e.state.y);
    else scrollToHash(false);
  });
});

function scrollToHash(flash) {
  const id = decodeURIComponent(location.hash.slice(1));
  if (!id) return window.scrollTo(0, 0);
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: el.classList.contains("stage") ? "start" : "center" });
  if (flash) {
    el.classList.remove("flash");
    void el.offsetWidth;
    el.classList.add("flash");
  }
}

// ---------------------------------------------------------------- nav

function renderNav(r) {
  const q = ($(".nav-search", nav)?.value || "").trim().toLowerCase();
  const doms = tree.domains.map((d) => {
    const active = d.tasks.filter((t) => t.state !== "done");
    const finished = d.tasks.filter((t) => t.state === "done");
    const asks = d.tasks.filter((t) => t.state === "ask").length;
    const taskLink = (t) => {
      const on = r.view === "task" && r.domain === d.id && r.task === t.id;
      const toc = on ? `<nav class="toc">${t.stages.map((s, i) => s.status === "skip"
        ? `<span class="step skip" data-n="${i + 1}"><b>${esc(s.title)}</b><span>건너뜀</span></span>`
        : `<a class="step ${s.status}" data-n="${i + 1}" href="#${s.key}" title="${esc(s.summary)}"><b>${esc(s.title)}</b><span>${esc(s.summary)}</span></a>`).join("")}</nav>` : "";
      return `<a class="task-link ${t.state}${on ? " on" : ""}" href="/${d.id}/${encodeURIComponent(t.id)}" data-find="${esc((t.id + " " + t.title).toLowerCase())}"><i></i><b>${esc(t.id)}</b><span>${esc(t.title)}</span></a>${toc}`;
    };
    const open = r.domain === d.id || (q && (d.id + d.title).toLowerCase().includes(q));
    return `<details class="dom" data-find="${esc((d.id + " " + d.title).toLowerCase())}"${open ? " open" : ""}>
      <summary><a href="/${d.id}/">${esc(d.title)}</a><span class="cnt${asks ? " ask" : ""}">${asks ? `질문 ${asks}` : active.length || ""}</span></summary>
      <div class="dom-body">
        <a class="nav-link${r.view === "domain" && r.domain === d.id ? " on" : ""}" href="/${d.id}/">화면 · SOT 맵</a>
        ${active.map(taskLink).join("")}
        ${finished.length ? `<details class="done-tasks"${finished.some((t) => r.task === t.id) ? " open" : ""}><summary>끝난 작업 ${finished.length}</summary>${finished.map(taskLink).join("")}</details>` : ""}
      </div></details>`;
  }).join("");
  const legacy = tree.legacy.map((p) => {
    const href = p.endsWith(".md") ? `/legacy/${p}` : `/files/${p}`;
    return `<li data-find="${esc(p.toLowerCase())}"><a href="${esc(href)}"${p.endsWith(".html") ? ' target="_blank"' : ""} class="${r.view === "legacy" && r.path === p ? "on" : ""}">${esc(p)}</a></li>`;
  }).join("");
  const searchVal = $(".nav-search", nav)?.value || "";
  nav.innerHTML = `<div class="nav-head"><b>${esc(tree.repo)}</b><span>${esc(tree.branch)}</span></div>
    <input class="nav-search" type="search" placeholder="찾기 — 도메인 · 작업 · 파일" value="${esc(searchVal)}">
    <a class="home${r.view === "home" ? " on" : ""}" href="/">전체 문서</a>
    <div class="nav-group">도메인</div>${doms || '<p class="note">아직 없어요</p>'}
    ${tree.legacy.length ? `<details class="legacy"${q || r.view === "legacy" ? " open" : ""}><summary>레거시 문서 ${tree.legacy.length}</summary><ul>${legacy}</ul></details>` : ""}
    <div class="legend"><span><i class="l-done"></i>완료</span><span><i class="l-now"></i>진행 중</span><span><i class="l-ask"></i>질문 · 결정 대기</span><span><i class="l-wait"></i>시작 전</span></div>`;
  const input = $(".nav-search", nav);
  input.addEventListener("input", () => filterNav(input.value));
  if (q) filterNav(q);
}

function filterNav(value) {
  const q = value.trim().toLowerCase();
  $$(".dom", nav).forEach((dom) => {
    let any = !q || dom.dataset.find.includes(q);
    $$(".task-link", dom).forEach((t) => {
      const hit = !q || t.dataset.find.includes(q) || dom.dataset.find.includes(q);
      t.classList.toggle("hide", !hit);
      if (hit && q) any = true;
    });
    dom.classList.toggle("hide", !any);
    if (q && any) dom.open = true;
  });
  $$(".legacy li", nav).forEach((li) => li.classList.toggle("hide", !!q && !li.dataset.find.includes(q)));
  const legacy = $(".legacy", nav);
  if (legacy && q) legacy.open = $$(".legacy li:not(.hide)", nav).length > 0;
}

// ---------------------------------------------------------------- shared pieces

function conclusion(st, items, editable) {
  const lis = (items || []).map((c, i) => `<li${editable ? ` data-editable="conclusion" data-i="${i}"` : ""}>${rich(c)}</li>`).join("");
  return `<section class="conclusion" data-status="${st}"><h2>결론</h2><ul>${lis || "<li>아직 없어요.</li>"}</ul></section>`;
}

function checklist(block, editable) {
  const items = (block.items || []).map((it) => {
    const rows = (it.rows || []).map(([label, text]) => `<li><span class="label">${esc(label)}:</span> ${rich(text)}</li>`).join("");
    return `<li id="${esc(it.id)}" class="${it.done ? "done" : ""}${it.by === "user" ? " by-user" : ""}"><label><input type="checkbox" data-check="${esc(it.id)}"${it.done ? " checked" : ""}${editable ? "" : " disabled"}> <span><b>${rich(it.title)}</b></span></label>${rows ? `<ul>${rows}</ul>` : ""}</li>`;
  }).join("");
  return `<h2${block.id ? ` id="${esc(block.id)}"` : ""}>${esc(block.title || "")}</h2><ul class="check">${items || '<li class="note">아직 없어요.</li>'}</ul>`;
}

const copyMarks = (html) => html.replace(/“([^”]+)”/g, '<span class="copy">$1</span>');

function quotes(items) {
  const groups = [];
  for (const q of items) {
    const src = q.source || "";
    if (!groups.length || groups.at(-1).src !== src) groups.push({ src, items: [] });
    groups.at(-1).items.push(q);
  }
  return `<div class="quotes">${groups.map((g) => `<section class="qgroup">${g.src ? `<h4>${rich(g.src)}</h4>` : ""}<ul>${g.items.map((q) => `<li>${copyMarks(rich(q.text))}</li>`).join("")}</ul></section>`).join("")}</div>`;
}

function blocks(stage, editable) {
  return (stage.blocks || []).map((b, bi) => {
    if (b.type === "checklist") return checklist(b, editable);
    if (b.type === "quote") return `<h2>${esc(b.title || "인용")}</h2>${quotes(b.items || [])}`;
    if (b.type === "table") {
      const head = (b.columns || []).map((c) => `<th>${esc(c)}</th>`).join("");
      const rows = (b.rows || []).map((r) => `<tr>${r.map((c, i) => `<td>${i === 0 ? `<b>${copyMarks(rich(c))}</b>` : copyMarks(rich(c))}</td>`).join("")}</tr>`).join("");
      return `<h2>${esc(b.title || "")}</h2><table class="tbl"><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`;
    }
    return `<h2${b.id ? ` id="${esc(b.id)}"` : ""}>${esc(b.title || "")}</h2><div class="${b.by === "user" ? "by-user" : ""}"${editable ? ` data-editable="block" data-b="${bi}"` : ""}>${rich(b.html || "")}</div>`;
  }).join("");
}

// ---------------------------------------------------------------- SOT map

function frameBoxes(xmlText) {
  const doc = new DOMParser().parseFromString(xmlText, "application/xml");
  const root = doc.documentElement;
  const boxes = {};
  const walk = (node, ox, oy, top) => {
    const x = ox + (top ? 0 : parseFloat(node.getAttribute("x") || 0));
    const y = oy + (top ? 0 : parseFloat(node.getAttribute("y") || 0));
    boxes[node.getAttribute("id")] = [x, y, parseFloat(node.getAttribute("width") || 0), parseFloat(node.getAttribute("height") || 0)];
    for (const c of node.children) walk(c, x, y, false);
  };
  walk(root, 0, 0, true);
  return { width: parseFloat(root.getAttribute("width")), height: parseFloat(root.getAttribute("height")), boxes };
}

function place(m, width, boxes) {
  if (!m.node) return [m.x, m.y];
  const b = boxes[m.node];
  if (!b) return null;
  const [x, y, w, h] = b;
  if (m.side === "top") return [x + w / 2, Math.max(12, y - 12)];
  if (m.side === "bottom") return [x + w / 2, y + h + 12];
  const right = x + w + 14;
  if (m.side === "left" || right > width - 12) return [Math.max(12, x - 14), y + h / 2];
  return [right, y + h / 2];
}

function usedBy(d) {
  const used = {};
  for (const t of d.tasks) {
    for (const [key, stage] of Object.entries(t.data.stages || {})) {
      walkRefs(stage, null, (raw, owner) => {
        const ref = parseRef(raw, { domain: d.id, task: t.data.id });
        if (ref.domain !== d.id || !ref.item || !/^[SX]\d+$/.test(ref.item) || ref.task) return;
        const label = owner ? `${t.data.id} ${owner}` : `${t.data.id} ${STAGES.find(([k]) => k === key)?.[1] || key}`;
        const href = `/${d.id}/${encodeURIComponent(t.data.id)}#${owner || key}`;
        (used[ref.item] ||= new Map()).set(href, label);
      });
    }
  }
  return used;
}

function usedHtml(map) {
  if (!map) return "";
  return `<div class="used">쓰는 곳 ${[...map].map(([href, label]) => `<a class="ref" href="${esc(href)}">${esc(label)}</a>`).join(" ")}</div>`;
}

async function sotMap(d) {
  const sot = d.screens?.data;
  if (!sot) return '<p class="note">아직 SOT 맵이 없어요.</p>';
  const comp = d.domain.data.kind === "components";
  const fieldHead = comp ? "속성 · 토큰" : "서버 필드";
  const offIntro = comp ? "Figma에 그려지지 않았지만 코드가 다뤄야 하는 경우예요." : "Figma 화면에는 없지만 데이터 때문에 생기는 경우예요.";
  const used = usedBy(d);
  const counts = {};
  const parts = [];
  for (const f of sot.flows || []) {
    parts.push(`<h2>흐름 · ${esc(f.title)}</h2><table><thead><tr><th>언제</th><th>결과</th></tr></thead><tbody>${f.rows.map(([a, b]) => `<tr><td>${rich(a)}</td><td>${rich(b)}</td></tr>`).join("")}</tbody></table>`);
  }
  for (const s of sot.screens || []) {
    let frame = null;
    try { frame = frameBoxes(await (await fetch(`/files/${d.id}/${s.metadata}`)).text()); } catch {}
    const pins = [], groups = [];
    for (const m of s.markers || []) {
      const [label, cls] = KIND[m.kind] || ["?", "pend"];
      counts[label] = (counts[label] || 0) + 1;
      const xy = frame ? place(m, frame.width, frame.boxes) : null;
      if (xy) pins.push(`<button class="pin k-${cls}" data-i="${esc(m.id)}" data-x="${(xy[0] / frame.width) * 100}" data-y="${(xy[1] / frame.height) * 100}">${esc(m.id.slice(1))}</button>`);
      const u = usedHtml(used[m.id]);
      const row = `<tr id="${esc(m.id)}" data-i="${esc(m.id)}"><td><span class="mk k-${cls}">${esc(m.id.slice(1))}</span></td><td><b>${rich(m.title)}</b><br><span class="k ${cls}">${label}</span></td><td>${rich(m.field || "—")}</td><td>${rich(m.rule || "")}${m.note ? `<div class="nt">${rich(m.note)}</div>` : ""}${u}</td></tr>`;
      const sec = m.section || "화면 요소";
      if (!groups.length || groups.at(-1)[0] !== sec) groups.push([sec, []]);
      groups.at(-1)[1].push(row);
    }
    const tables = groups.map(([sec, rows]) => `<h3>${esc(sec)}</h3><table><thead><tr><th></th><th>${comp ? "부분" : "요소"}</th><th>${fieldHead}</th><th>규칙 · 근거</th></tr></thead><tbody>${rows.join("")}</tbody></table>`).join("");
    const off = (s.offscreen || []).length ? `<h3>화면 밖 상태</h3><p class="note">${esc(s.offscreenIntro || offIntro)}</p><table><thead><tr><th></th><th>상태</th><th>언제</th><th>보이는 것</th></tr></thead><tbody>${s.offscreen.map((o) => `<tr id="${esc(o.id)}"><td><span class="mk k-out">${esc(o.id)}</span></td><td><b>${rich(o.state)}</b>${usedHtml(used[o.id])}</td><td>${rich(o.when)}</td><td>${rich(o.shows)}</td></tr>`).join("")}</tbody></table>` : "";
    const land = frame && (frame.width > frame.height || frame.width > 700);
    const shot = frame
      ? `<div class="shot"><div class="fig" data-w="${frame.width}" data-h="${frame.height}"><img src="/files/${esc(d.id)}/${esc(s.image)}" alt="${esc(s.title)} Figma 화면">${pins.join("")}</div></div>`
      : `<div class="shot"><p class="note">구조 정보(${esc(s.metadata)})를 읽지 못했어요.</p></div>`;
    const variants = (s.variants || []).length ? `<h3>변형 축</h3><table class="tbl"><thead><tr><th>Figma 축</th><th>값</th><th>코드 속성</th><th>메모</th></tr></thead><tbody>${s.variants.map((v) => `<tr><td><b>${esc(v.axis)}</b></td><td>${rich(v.values)}</td><td>${rich(v.prop || "")}</td><td>${rich(v.note || "")}</td></tr>`).join("")}</tbody></table>` : "";
    parts.push(`<h2 class="screen" id="screen-${esc(s.id)}">${comp ? "컴포넌트" : "화면"} · ${esc(s.title)}</h2><p class="meta">Figma <code>${esc(s.figma || "")}</code></p><div class="cols${land ? " landscape" : ""}">${shot}<div>${variants}${tables}${off}</div></div>`);
  }
  const chips = Object.entries(counts).map(([k, v]) => `<span>${esc(k)} ${v}</span>`).join("");
  const meta = [sot.api ? `API <code>${esc(sot.api)}</code>` : "", sot.base ? `기준 ${esc(sot.base)}` : ""].filter(Boolean).join(" · ");
  return `${meta ? `<p class="meta">${meta}</p>` : ""}${chips ? `<div class="sum">${chips}</div>` : ""}${parts.join("")}`;
}

function wireSot(root) {
  $$(".fig", root).forEach((fig) => {
    const w = Number(fig.dataset.w), h = Number(fig.dataset.h);
    const landscape = fig.closest(".cols")?.classList.contains("landscape");
    fig.style.width = landscape ? `min(100%, ${w}px, calc((48vh - 32px) * ${w / h}))` : `min(100%, ${w}px)`;
    $$(".pin", fig).forEach((p) => {
      p.style.left = p.dataset.x + "%";
      p.style.top = p.dataset.y + "%";
    });
  });
  const hot = (i, scrollFig) => {
    $$(".pin.hot, tr.hot", root).forEach((e) => e.classList.remove("hot"));
    const p = $(`.pin[data-i="${i}"]`, root), r = $(`tr[data-i="${i}"]`, root);
    if (!p || !r) return;
    p.classList.add("hot");
    r.classList.add("hot");
    const shot = p.closest(".shot");
    if (scrollFig && shot) shot.scrollTop = p.offsetTop - shot.clientHeight / 2;
  };
  $$("tbody tr[data-i]", root).forEach((r) => r.addEventListener("mouseenter", () => hot(r.dataset.i, true)));
  $$(".pin", root).forEach((p) => p.addEventListener("click", () => {
    $(`tr[data-i="${p.dataset.i}"]`, root)?.scrollIntoView({ behavior: "smooth", block: "center" });
    hot(p.dataset.i, false);
  }));
}

// ---------------------------------------------------------------- pages

function homePage() {
  const rows = tree.domains.map((d) => {
    const active = d.tasks.filter((t) => t.state !== "done");
    const list = active.length
      ? active.map((t) => `<div><a href="/${d.id}/${encodeURIComponent(t.id)}">${esc(t.id)} ${esc(t.title)}</a> <span class="st ${t.state}">${STATE_LABEL[t.state]}</span></div>`).join("")
      : `<span class="note">진행 중인 작업 없음</span>`;
    return `<div class="row"><h3><a href="/${d.id}/">${esc(d.title)}</a><small>${esc(d.id)} · 작업 ${d.tasks.length}</small></h3><div>${list}</div></div>`;
  }).join("");
  page.innerHTML = `<div class="head"><h1>${esc(tree.repo)}</h1><p class="meta">${esc(tree.branch)} · 도메인 ${tree.domains.length} · 레거시 문서 ${tree.legacy.length}</p></div>
    <div class="cards">${rows || '<p class="note">아직 flow 도메인이 없어요.</p>'}</div>`;
  document.title = `${tree.repo} · flow`;
}

async function domainPage(id) {
  const d = await loadDomain(id, true);
  const notes = restoreDrafts(d);
  const dom = d.domain.data;
  const links = (dom.links || []).map((l) => `<li><a href="${esc(l.url)}" target="_blank">${esc(l.label)}</a></li>`).join("");
  const tasks = d.tasks.map((t) => {
    const st = taskState(t.data);
    return `<div class="row"><h3><a href="/${id}/${encodeURIComponent(t.data.id)}">${esc(t.data.id)}</a><small>${esc(t.data.type || "")}</small></h3><div>${esc(t.data.title)} <span class="st ${st}">${STATE_LABEL[st]}</span></div></div>`;
  }).join("");
  page.className = "page wide";
  page.innerHTML = `<div class="head"><h1>${esc(dom.title || id)}</h1><p class="meta">도메인 <code>${esc(id)}</code>${dom.figma ? ` · Figma <code>${esc(dom.figma)}</code>` : ""}</p></div>
    ${noticeHtml(notes)}${links ? `<ul class="links">${links}</ul>` : ""}
    <h2>작업</h2><div class="cards">${tasks || '<p class="note">아직 없어요.</p>'}</div>
    ${await sotMap(d)}`;
  wireSot(page);
  wireNotices(notes, d);
  markBroken(page);
  document.title = `${dom.title || id} · flow`;
}

function stageSection(entry, key, title, n) {
  const t = entry.data;
  const stage = t.stages[key];
  const s = stageState(t, key);
  let body = "";
  if (key === "grill") body = grillBody(stage, s);
  else {
    body = conclusion(s.status, stage.conclusion, true) + blocks(stage, true);
    if (key === "screen") body += screenRefs(t);
  }
  return `<section class="stage" id="${key}" data-status="${s.status}" data-stage="${key}"><h1><span class="n">${n}</span>${esc(title)}</h1>${body}</section>`;
}

function screenRefs(t) {
  const seen = new Set();
  walkRefs(t.stages || {}, null, (raw) => {
    const r = parseRef(raw, { domain: ctx.domain, task: t.id });
    if (r.domain === ctx.domain && !r.task && /^[SX]\d+$/.test(r.item || "")) seen.add(r.item);
  });
  if (!seen.size) return `<h2>SOT 맵</h2><p><a href="/${ctx.domain}/">도메인 SOT 맵 보기</a></p>`;
  const ids = [...seen].sort((a, b) => a[0].localeCompare(b[0]) || Number(a.slice(1)) - Number(b.slice(1)));
  return `<h2>이 작업이 쓰는 행</h2><p>${ids.map((i) => rich(`[[${i}]]`)).join(" ")} · <a href="/${ctx.domain}/">도메인 SOT 맵 전체</a></p>`;
}

function grillBody(stage, s) {
  const concl = [];
  for (const r of stage.rounds || []) {
    const open = (r.questions || []).some((q) => !q.decision);
    if (!open) concl.push(...r.questions.map((q) => q.decision));
  }
  s.open.forEach((id) => concl.push(`${id}이 열려 있어요. 답을 기다려요.`));
  s.revised.forEach((id) => concl.push(`${id}의 답이 바뀌었어요. 결정은 바뀌기 전 내용이라 Claude가 다시 반영해야 해요.`));
  const forms = [...(stage.rounds || [])].reverse().map((r) => {
    const open = s.open.includes(r.id), revised = s.revised.includes(r.id);
    const cards = (r.questions || []).map((q) => {
      const a = q.answer || {};
      const opts = [...(q.options || [{ value: "yes", label: "추천대로" }, { value: "no", label: "다르게" }]), { value: "unsure", label: "더 설명해줘" }];
      const rec = q.recommended || "yes";
      const radios = opts.map((o) => `<label class="${o.value === rec ? "rec" : ""}"><input type="radio" name="${esc(r.id)}-${esc(q.id)}" value="${esc(o.value)}"${a.choice === o.value ? " checked" : ""}>${esc(o.label)}</label>`).join("");
      const decision = q.decision ? `<div class="decision"><b>결정</b> ${rich(q.decision)}<div class="applied">반영한 곳: ${rich(q.appliedTo || "")}</div></div>` : "";
      return `<div class="q${a.by === "user" ? " by-user-q" : ""}" id="${esc(r.id)}-${esc(q.id)}" data-round="${esc(r.id)}" data-q="${esc(q.id)}"><b>${esc(r.id)}-${esc(q.id)}. ${rich(q.title)}</b>${a.by === "user" ? '<span class="badge pending">사람이 답함 · 반영 전</span>' : ""}
        <div class="said">${rich(q.said || "")}</div><div>${rich(q.body || "")}</div>
        <div class="rec-line"><b>추천</b> ${rich(q.recommendation || "")}</div><div class="opts">${radios}</div>
        <textarea data-note placeholder="메모 (다르게 고르면 조건을 적어 주세요)">${esc(a.note || "")}</textarea>
        <textarea data-follow placeholder="되묻고 싶은 것">${esc(a.followUp || "")}</textarea>${decision}</div>`;
    }).join("");
    const badge = open ? '<span class="badge open">답을 기다려요</span>' : revised ? '<span class="badge revised">답이 바뀜 · 반영 전</span>' : '<span class="badge settled">결정됨 · 고칠 수 있어요</span>';
    const inner = open || revised ? cards : `<details><summary>질문 ${(r.questions || []).length}개 펼치기 · 답을 바꾸려면 펼쳐서 고치고 저장</summary>${cards}</details>`;
    return `<div class="round-form ${open ? "open" : revised ? "revised" : ""}" id="${esc(r.id)}"><h2>${esc(r.id)} · ${esc(r.askedAt || "")} · ${rich(r.from || "")}${badge}</h2>${inner}</div>`;
  }).join("");
  return conclusion(s.status, concl.length ? concl : ["아직 질문이 없어요."], false) + forms;
}

async function taskPage(domainId, taskId) {
  const d = await loadDomain(domainId, true);
  const notes = restoreDrafts(d);
  const entry = d.tasks.find((t) => t.data.id === taskId);
  if (!entry) {
    page.innerHTML = `<div class="head"><h1>없는 작업</h1><p class="meta">${esc(domainId)} / ${esc(taskId)}</p></div>`;
    return;
  }
  const t = entry.data;
  const links = (t.links || []).map((l) => `<li><a href="${esc(l.url)}" target="_blank">${esc(l.label)}</a></li>`).join("");
  const stages = STAGES.map(([k, title], i) => (t.stages?.[k] ? stageSection(entry, k, title, i + 1) : "")).join("");
  const skipped = STAGES.map(([k, title], i) => (t.stages?.[k] ? null : `${i + 1} ${title}`)).filter(Boolean);
  page.className = "page";
  page.innerHTML = `<div class="head"><h1>${esc(t.title)}</h1><p class="meta">${[esc(d.domain.data.title || domainId), esc(t.id), esc(t.type || ""), t.branch ? `<code>${esc(t.branch)}</code>` : ""].filter(Boolean).join(" · ")}</p>
    ${links ? `<ul class="links">${links}</ul>` : ""}</div>${noticeHtml(notes)}${stages}
    ${skipped.length ? `<p class="note index-note">건너뛴 단계: ${esc(skipped.join(", "))}. 필요해지면 그때 만들어요.</p>` : ""}`;
  wireTask(page, entry);
  wireNotices(notes, d);
  markBroken(page);
  document.title = `${t.id} ${t.title} · flow`;
}

async function legacyPage(p) {
  const text = await (await fetch(`/files/${p}`)).text();
  page.className = "page";
  page.innerHTML = `<div class="head"><p class="meta">레거시 문서 · <code>${esc(p)}</code> · 읽기 전용 · <a href="/files/${esc(p)}" target="_blank">원본</a></p></div><article class="md">${markdown(text, p)}</article>`;
  document.title = `${p} · flow`;
}

// ---------------------------------------------------------------- edits

function wireTask(root, entry) {
  const t = entry.data;
  const changed = () => {
    markDirty(entry);
    refreshNavFromLocal();
  };
  $$("input[data-check]", root).forEach((input) => input.addEventListener("change", () => {
    const sec = input.closest(".stage");
    const stage = t.stages[sec.dataset.stage];
    for (const b of stage.blocks || []) {
      const it = (b.items || []).find((x) => x.id === input.dataset.check);
      if (it) {
        it.done = input.checked;
        it.by = "user";
        input.closest("li").classList.toggle("done", input.checked);
        input.closest("li").classList.add("by-user");
      }
    }
    changed();
  }));
  $$(".q", root).forEach((card) => {
    const update = () => {
      const r = t.stages.grill.rounds.find((x) => x.id === card.dataset.round);
      const q = r.questions.find((x) => x.id === card.dataset.q);
      const choice = $("input[type=radio]:checked", card)?.value || "";
      q.answer = { choice, note: $("[data-note]", card).value, followUp: $("[data-follow]", card).value, by: "user" };
      card.classList.add("by-user-q");
      if (!$(".badge.pending", card)) $("b", card).insertAdjacentHTML("afterend", '<span class="badge pending">사람이 답함 · 반영 전</span>');
      changed();
    };
    $$("input[type=radio]", card).forEach((i) => i.addEventListener("change", update));
    $$("textarea", card).forEach((ta) => ta.addEventListener("change", update));
  });
  $$("[data-editable]", root).forEach((el) => {
    el.title = "두 번 눌러 고치기";
    el.addEventListener("dblclick", (e) => {
      if (e.target.closest("a")) return;
      el.contentEditable = "true";
      el.focus();
    });
    el.addEventListener("blur", () => {
      if (el.contentEditable !== "true") return;
      el.contentEditable = "false";
      const sec = el.closest(".stage");
      const stage = t.stages[sec.dataset.stage];
      const value = unrich(el);
      if (el.dataset.editable === "conclusion") {
        if (stage.conclusion[el.dataset.i] === value) return;
        stage.conclusion[el.dataset.i] = value;
        stage.by = "user";
      } else {
        const b = stage.blocks[el.dataset.b];
        if (b.html === value) return;
        b.html = value;
        b.by = "user";
        el.classList.add("by-user");
      }
      changed();
    });
  });
}

function refreshNavFromLocal() {
  for (const d of tree.domains) {
    const loaded = domains.get(d.id);
    if (!loaded) continue;
    d.tasks = loaded.tasks.map((e) => ({
      id: e.data.id, title: e.data.title, type: e.data.type || "", state: taskState(e.data),
      stages: STAGES.map(([k, title]) => ({ key: k, title, ...stageState(e.data, k) })),
    }));
  }
  renderNav(route());
}

function renderSavebar() {
  if (!dirty.size) {
    savebar.hidden = true;
    return;
  }
  savebar.hidden = false;
  savebar.innerHTML = `<span>저장 안 한 파일 ${dirty.size}</span><button class="ghost" data-copy>복사</button><button data-save>저장</button>`;
  $("[data-save]", savebar).onclick = saveAll;
  $("[data-copy]", savebar).onclick = copyAll;
}

async function saveAll() {
  const files = [...dirty.values()].map((e) => ({ path: e.path, hash: e.hash, data: e.data }));
  try {
    const res = await getJson("/api/save", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ files }) });
    for (const s of res.saved) {
      const e = dirty.get(s.path);
      e.hash = s.hash;
      dirty.delete(s.path);
      try { localStorage.removeItem(draftKey(s.path)); } catch {}
    }
    renderSavebar();
    toast("저장했어요 · 채팅에 '저장했어'라고 알려 주세요");
    lastVersion = (await getJson("/api/version")).version;
    await render();
  } catch (e) {
    if (e.status === 409) {
      toast(`${e.body.path}을 그 사이 Claude가 고쳤어요. 고친 내용은 이 브라우저에 남아 있어요 — 새로고침 후 다시 확인해 주세요`, true);
    } else if (!e.status) {
      toast("서버에 연결할 수 없어요. '복사'를 눌러 채팅에 붙여넣어 주세요", true);
    } else toast(`저장 실패: ${e.message}`, true);
  }
}

async function copyAll() {
  const files = [...dirty.values()].map((e) => ({ path: e.path, data: e.data }));
  const text = "flow 변경 — 아래 내용을 각 파일에 써 주세요\n```json\n" + JSON.stringify(files, null, 2) + "\n```";
  try {
    await navigator.clipboard.writeText(text);
    toast("복사했어요 · 채팅에 붙여넣어 주세요");
  } catch {
    toast("복사하지 못했어요", true);
  }
}

function noticeHtml(notes) {
  return notes.map((n, i) => n.kind === "restored"
    ? `<div class="notice" data-n="${i}">저장하지 않은 변경을 되살렸어요 · <code>${esc(n.path)}</code><button data-discard>버리기</button></div>`
    : `<div class="notice" data-n="${i}">저장하지 않은 변경이 남아 있는데, 그 사이 파일이 바뀌었어요 · <code>${esc(n.path)}</code><button data-copy>복사</button><button data-discard>버리기</button></div>`).join("");
}

function wireNotices(notes, d) {
  $$(".notice[data-n]", page).forEach((el) => {
    const n = notes[Number(el.dataset.n)];
    $("[data-discard]", el)?.addEventListener("click", async () => {
      try { localStorage.removeItem(draftKey(n.path)); } catch {}
      dirty.delete(n.path);
      renderSavebar();
      await render();
    });
    $("[data-copy]", el)?.addEventListener("click", async () => {
      await navigator.clipboard.writeText("flow 변경 — 파일이 그 사이 바뀌어서 저장하지 못한 내용\n```json\n" + JSON.stringify({ path: n.path, data: n.draft.data }, null, 2) + "\n```");
      toast("복사했어요 · 채팅에 붙여넣어 주세요");
    });
  });
}

// ---------------------------------------------------------------- markdown (legacy, read only)

function markdown(src, file) {
  const base = file.split("/").slice(0, -1).join("/");
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, t, u) => {
      let href = u;
      if (!/^[a-z]+:|^\/|^#/.test(u)) {
        const parts = (base ? base.split("/") : []);
        for (const seg of u.split("/")) { if (seg === "..") parts.pop(); else if (seg !== ".") parts.push(seg); }
        const rel = parts.join("/");
        href = rel.endsWith(".md") ? `/legacy/${rel}` : `/files/${rel}`;
      }
      return `<a href="${href}">${t}</a>`;
    });
  const lines = src.split("\n");
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^```/.test(l)) {
      const buf = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++;
      out.push(`<pre><code>${esc(buf.join("\n"))}</code></pre>`);
      continue;
    }
    const h = l.match(/^(#{1,4})\s+(.*)/);
    if (h) { out.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`); i++; continue; }
    if (/^\|/.test(l)) {
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++]);
      const cells = (r) => r.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const body = rows.filter((r) => !/^\|[\s:|-]+\|$/.test(r));
      out.push(`<table><thead><tr>${cells(body[0]).map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${body.slice(1).map((r) => `<tr>${cells(r).map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
      continue;
    }
    if (/^\s*([-*]|\d+\.)\s/.test(l)) {
      const items = [];
      while (i < lines.length && /^\s*([-*]|\d+\.)\s/.test(lines[i])) items.push(lines[i++].replace(/^\s*([-*]|\d+\.)\s/, ""));
      out.push(`<ul>${items.map((x) => `<li>${inline(x.replace(/^\[( |x)\]\s*/, (m, c) => (c === "x" ? "☑ " : "☐ ")))}</li>`).join("")}</ul>`);
      continue;
    }
    if (/^>\s?/.test(l)) {
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, ""));
      out.push(`<blockquote>${inline(buf.join(" "))}</blockquote>`);
      continue;
    }
    if (/^---+$/.test(l.trim())) { out.push("<hr>"); i++; continue; }
    if (!l.trim()) { i++; continue; }
    const buf = [];
    while (i < lines.length && lines[i].trim() && !/^(#|```|\||>|\s*([-*]|\d+\.)\s)/.test(lines[i])) buf.push(lines[i++]);
    out.push(`<p>${inline(buf.join(" "))}</p>`);
  }
  return out.join("\n");
}

// ---------------------------------------------------------------- main

async function render() {
  const r = route();
  ctx = { domain: r.domain || null, task: r.task || null };
  tree = await getJson("/api/tree");
  if (r.view === "home") { page.className = "page"; homePage(); }
  else if (r.view === "domain") await domainPage(r.domain);
  else if (r.view === "task") await taskPage(r.domain, r.task);
  else if (r.view === "legacy") await legacyPage(r.path);
  if (r.domain && domains.has(r.domain)) refreshNavFromLocal();
  else renderNav(r);
  renderSavebar();
}

async function poll() {
  try {
    const { version } = await getJson("/api/version");
    if (lastVersion && version !== lastVersion) {
      if (!dirty.size) {
        const y = window.scrollY;
        await render();
        window.scrollTo(0, y);
        toast("파일이 바뀌어서 다시 불러왔어요");
      } else toast("Claude가 파일을 고쳤어요. 저장하면 충돌할 수 있어요 — 먼저 저장하거나 복사해 두세요", true);
    }
    lastVersion = version;
  } catch {}
}

const KEY = "flow-nav-collapsed";
const toggle = () => {
  const v = !document.documentElement.classList.contains("nav-collapsed");
  document.documentElement.classList.toggle("nav-collapsed", v);
  try { localStorage.setItem(KEY, v ? "1" : ""); } catch {}
};
$("#navtoggle").addEventListener("click", toggle);
document.addEventListener("keydown", (e) => {
  if (e.key === "[" && !/input|textarea|select/i.test(e.target.tagName) && !e.target.isContentEditable) toggle();
});
requestAnimationFrame(() => requestAnimationFrame(() => document.documentElement.classList.add("nav-ready")));
window.addEventListener("beforeunload", (e) => {
  if (dirty.size) e.preventDefault();
});

render().then(() => scrollToHash(false)).catch((e) => {
  page.innerHTML = `<div class="head"><h1>불러오지 못했어요</h1><p class="meta">${esc(e.message)}</p></div>`;
});
getJson("/api/version").then((v) => (lastVersion = v.version)).catch(() => {});
setInterval(poll, 3000);
