(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const data = JSON.parse($("#flow-data").textContent);
  const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } },
    del(k) { try { localStorage.removeItem(k); } catch (e) {} },
  };

  const toastEl = $("#toast");
  const toast = (text) => {
    toastEl.textContent = text;
    toastEl.classList.add("show");
    clearTimeout(toast.t);
    toast.t = setTimeout(() => toastEl.classList.remove("show"), 2600);
  };

  // ------------------------------------------------------------ nav

  const NAV = "flow-nav-collapsed";
  const setNav = (v) => {
    document.body.classList.toggle("collapsed", v);
    store.set(NAV, v ? "1" : "");
  };
  $("#navtoggle").addEventListener("click", () => setNav(!document.body.classList.contains("collapsed")));
  document.addEventListener("keydown", (e) => {
    if (e.key === "[" && !/input|textarea|select/i.test(e.target.tagName)) setNav(!document.body.classList.contains("collapsed"));
  });

  // ------------------------------------------------------------ references

  const peek = $("#peek");
  document.addEventListener("mouseover", (e) => {
    const a = e.target.closest && e.target.closest("a.ref[data-raw]");
    if (!a) return;
    const item = (data.refs || {})[a.dataset.raw];
    peek.innerHTML = item
      ? `<div class="where">${esc(item.where)}</div><b>${item.title}</b><div>${item.body || ""}</div>`
      : `<b>${esc(a.dataset.raw)}</b>찾을 수 없는 참조예요`;
    const r = a.getBoundingClientRect();
    peek.hidden = false;
    const w = peek.offsetWidth, h = peek.offsetHeight;
    peek.style.left = Math.min(window.innerWidth - w - 12, Math.max(12, r.left)) + "px";
    peek.style.top = (r.bottom + h + 12 > window.innerHeight ? r.top - h - 8 : r.bottom + 8) + "px";
  });
  document.addEventListener("mouseout", (e) => {
    if (e.target.closest && e.target.closest("a.ref")) peek.hidden = true;
  });

  // ------------------------------------------------------------ SOT map

  $$(".fig").forEach((fig) => {
    const w = Number(fig.dataset.w), h = Number(fig.dataset.h);
    const landscape = fig.closest(".cols") && fig.closest(".cols").classList.contains("landscape");
    fig.style.width = landscape ? `min(100%, ${w}px, calc((48vh - 32px) * ${w / h}))` : `min(100%, ${w}px)`;
    $$(".pin", fig).forEach((p) => {
      p.style.left = p.dataset.x + "%";
      p.style.top = p.dataset.y + "%";
    });
  });
  const hot = (i, scrollFig) => {
    $$(".pin.hot, tr.hot").forEach((e) => e.classList.remove("hot"));
    const p = $(`.pin[data-i="${i}"]`), r = $(`tr[data-i="${i}"]`);
    if (!p || !r) return;
    p.classList.add("hot");
    r.classList.add("hot");
    const shot = p.closest(".shot");
    if (scrollFig && shot) shot.scrollTop = p.offsetTop - shot.clientHeight / 2;
  };
  $$("tbody tr[data-i]").forEach((r) => r.addEventListener("mouseenter", () => hot(r.dataset.i, true)));
  $$(".pin").forEach((p) => p.addEventListener("click", () => {
    const r = $(`tr[data-i="${p.dataset.i}"]`);
    if (r) r.scrollIntoView({ behavior: "smooth", block: "center" });
    hot(p.dataset.i, false);
  }));

  // ------------------------------------------------------------ jump to #id

  const jump = (smooth) => {
    const id = decodeURIComponent(location.hash.slice(1));
    const el = id && document.getElementById(id);
    if (!el) return;
    const small = el.matches("li, tr, .q");
    el.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: small ? "center" : "start" });
    if (el.matches("tr[data-i]")) hot(el.dataset.i, true);
    el.classList.remove("flash");
    void el.offsetWidth;
    el.classList.add("flash");
  };
  window.addEventListener("hashchange", () => jump(true));
  if (location.hash) requestAnimationFrame(() => jump(false));

  // ------------------------------------------------------------ answers

  const A = data.answers;
  if (!A) return;
  const KEY = "flow:" + decodeURIComponent(location.pathname.replace(/[^/]*$/, ""));
  const chromium = !!navigator.userAgentData;
  const readState = () => {
    try { return JSON.parse(store.get(KEY) || "null"); } catch (e) { return null; }
  };
  let st = readState();
  if (st && (st.updatedAt || 0) <= (A.pulledAt || 0)) {
    store.del(KEY);
    st = null;
  }
  st = st || { v: 1, task: A.task, updatedAt: 0, answers: {}, checks: {} };

  const DEFAULT_OPTS = [{ value: "yes", label: "추천대로" }, { value: "no", label: "다르게" }];
  const optsOf = (q) => [...(q.options && q.options.length ? q.options : DEFAULT_OPTS), { value: "unsure", label: "더 설명해줘" }];
  const FIELDS = ["choice", "note", "followUp", "copy"];
  const sameAnswer = (a, b) => FIELDS.every((k) => (a[k] || "") === (b[k] || ""));

  const save = () => {
    st.updatedAt = Date.now();
    const empty = !Object.keys(st.answers).length && !Object.keys(st.checks).length;
    if (empty) store.del(KEY);
    else if (!store.set(KEY, JSON.stringify(st))) toast("이 브라우저에 저장하지 못했어요 · '답 복사'를 써 주세요");
    paint();
  };

  $$(".q[data-tag]").forEach((card) => {
    const tag = card.dataset.tag;
    const local = st.answers[tag];
    if (local) {
      $$("input[type=radio]", card).forEach((i) => { i.checked = i.value === local.choice; });
      $$("textarea[data-f]", card).forEach((ta) => { ta.value = local[ta.dataset.f] || ""; });
    }
    const update = () => {
      const now = {
        choice: ($("input[type=radio]:checked", card) || {}).value || "",
        note: $("textarea[data-f=note]", card).value.trim(),
        followUp: $("textarea[data-f=followUp]", card).value.trim(),
        copy: ($("textarea[data-f=copy]", card) || { value: "" }).value.trim(),
      };
      if (sameAnswer(now, (A.questions[tag] || {}).answer || {})) delete st.answers[tag];
      else st.answers[tag] = now;
      save();
    };
    $$("input[type=radio]", card).forEach((i) => i.addEventListener("change", update));
    $$("textarea[data-f]", card).forEach((ta) => ta.addEventListener("input", update));
  });

  $$("input[data-check]").forEach((input) => {
    const id = input.dataset.check;
    if (id in st.checks) input.checked = st.checks[id];
    input.addEventListener("change", () => {
      if (input.checked === !!(A.checks[id] || {}).done) delete st.checks[id];
      else st.checks[id] = input.checked;
      save();
    });
  });

  const fmt = (t) => {
    const d = new Date(t), p = (n) => String(n).padStart(2, "0");
    return `${d.getMonth() + 1}/${d.getDate()} ${p(d.getHours())}:${p(d.getMinutes())}`;
  };

  const savebar = $("#savebar");
  const hasForms = $$(".q[data-tag], input[data-check]").length > 0;

  const answerOf = (tag) => st.answers[tag] || (A.questions[tag] || {}).answer || {};
  const previewOf = (card) => {
    const a = answerOf(card.dataset.tag);
    const pick = (a.copy && $('template[data-preview="copy"]', card)) || (a.choice && $(`template[data-preview="${CSS.escape(a.choice)}"]`, card));
    if (!pick) return null;
    const frag = pick.content.cloneNode(true);
    $$("[data-slot]", frag).forEach((slot) => { slot.textContent = a.copy || ""; });
    return frag;
  };

  function paint() {
    $$(".q[data-tag]").forEach((card) => {
      const tag = card.dataset.tag;
      const q = A.questions[tag] || {};
      const local = !!st.answers[tag];
      const a = answerOf(tag);
      const answered = !!(a.choice || a.copy || a.note);
      $$(`[data-status-for="${tag}"]`).forEach((chip) => {
        if (q.decided && !local) [chip.className, chip.textContent] = ["k done", "결정됨"];
        else if (answered) [chip.className, chip.textContent] = ["k ans", "답 있음 · 반영 전"];
        else [chip.className, chip.textContent] = ["k pend", chip.dataset.label];
      });
      $$(`tr[data-row-for="${tag}"]`).forEach((row) => row.classList.toggle("ask", !q.decided && !answered));
      const live = $("[data-live]", card);
      if (live) {
        $$(":scope > :not(template)", live).forEach((e) => e.remove());
        const frag = previewOf(card);
        if (frag) {
          const label = document.createElement("div");
          label.className = "ui-kind";
          label.textContent = "미리보기";
          live.append(label, frag);
        }
      }
      $$(`[data-preview-for="${tag}"]`).forEach((box) => {
        const frag = previewOf(card);
        box.hidden = !frag;
        box.replaceChildren();
        if (frag) {
          const b = document.createElement("b");
          b.textContent = q.decided && !local ? "확정 문구" : "답변 문구 (확정 전)";
          box.append(b, frag);
        }
      });
      const badge = $(".q-head .k", card);
      let cls, label;
      if (local) [cls, label] = ["k ans", "입력됨 · 반영 전"];
      else if (q.byUser) [cls, label] = ["k ans", "답 받음 · 반영 전"];
      else if (q.decided) [cls, label] = ["k done", "결정됨"];
      else [cls, label] = ["k pend", "답 대기"];
      badge.className = cls;
      badge.textContent = label;
      card.classList.toggle("open", !q.decided && !local && !q.byUser);
    });
    $$("input[data-check]").forEach((input) => {
      const li = input.closest("li");
      const id = input.dataset.check;
      li.classList.toggle("done", input.checked);
      let badge = $(":scope > .k:not(.srv)", li);
      if (id in st.checks) {
        if (!badge) {
          badge = document.createElement("span");
          $(":scope > label", li).after(badge);
        }
        badge.className = "k ans";
        badge.textContent = st.checks[id] ? "체크함 · 반영 전" : "체크 풂 · 반영 전";
      } else if (badge) badge.remove();
    });
    const n = Object.keys(st.answers).length + Object.keys(st.checks).length;
    savebar.hidden = !hasForms && !n;
    if (savebar.hidden) return;
    const how = chromium ? "채팅에 '답 썼어'라고 알려 주세요" : "'답 복사'를 누른 뒤 채팅에 '복사했어'라고 알려 주세요";
    savebar.innerHTML = n
      ? `<span>이 브라우저에 저장됨 · ${n}건 · ${fmt(st.updatedAt)}<br>${how}</span><button class="ghost" data-undo>되돌리기</button><button data-copy>답 복사</button>`
      : `<span>답을 고르면 이 브라우저에 자동으로 저장돼요</span><button data-copy>답 복사</button>`;
    $("[data-copy]", savebar).onclick = copy;
    const undo = $("[data-undo]", savebar);
    if (undo) undo.onclick = () => {
      if (!confirm("이 브라우저에 저장된 답과 체크를 지우고 페이지에 쓰인 내용으로 되돌릴까요?")) return;
      store.del(KEY);
      location.reload();
    };
  }

  const block = (label, text) => {
    const lines = String(text).split("\n");
    return [`  ${label}: ${lines[0]}`, ...lines.slice(1).map((l) => `    ${l}`)];
  };

  function copyText() {
    const out = [`[flow 답 · ${A.task} · ${fmt(st.updatedAt || Date.now())} · t=${st.updatedAt || 0}]`, A.title, ""];
    for (const [tag, q] of Object.entries(A.questions)) {
      const local = st.answers[tag];
      if (q.decided && !local) continue;
      const a = local || q.answer || {};
      const state = local ? "입력됨" : q.byUser ? "답 받음" : "답 대기";
      out.push(`${tag} ${q.title} (${state})`);
      const label = (optsOf(q).find((o) => o.value === a.choice) || {}).label;
      out.push(...block("답", label || "답 없음"));
      if (a.copy) out.push(...block("문구", a.copy));
      if (a.note) out.push(...block("메모", a.note));
      if (a.followUp) out.push(...block("되물음", a.followUp));
      out.push("");
    }
    const checks = Object.entries(st.checks);
    if (checks.length) {
      out.push("체크");
      for (const [id, done] of checks) out.push(`  [${done ? "x" : " "}] ${id} ${(A.checks[id] || {}).title || ""}`);
    }
    return out.join("\n").trim() + "\n";
  }

  async function copy() {
    const text = copyText();
    let ok = false;
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch (e) {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.append(ta);
      ta.select();
      ok = document.execCommand("copy");
      ta.remove();
    }
    toast(ok ? "복사했어요 · 슬랙에 붙이거나 채팅에 '복사했어'라고 알려 주세요" : "복사하지 못했어요");
  }

  if (hasForms && !chromium && store.get("flow-banner-off") !== "1") {
    const head = $(".page > .head");
    const div = document.createElement("div");
    div.className = "banner";
    div.innerHTML = "<p>이 브라우저에서 쓴 답은 Claude가 자동으로 읽지 못해요. Chrome · Aside에서 열거나, 답을 쓴 뒤 '답 복사'를 눌러 주세요.</p><button>닫기</button>";
    $("button", div).onclick = () => {
      store.set("flow-banner-off", "1");
      div.remove();
    };
    (head || $(".page")).after(div);
  }
  paint();
})();
