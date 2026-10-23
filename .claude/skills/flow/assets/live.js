(function () {
  var meta = document.querySelector('meta[name="flow-task"]');
  if (!meta) return;
  var TASK = meta.content;
  var FILE = decodeURIComponent(location.pathname.split("/").pop() || "index.html");
  var hasInputs = !!document.querySelector("[data-check], .round-form");
  var supported = typeof window.showDirectoryPicker === "function";

  var bar = document.createElement("div");
  bar.className = "connect";
  var toast = document.createElement("div");
  toast.className = "toast";
  document.body.insertBefore(bar, document.querySelector("main"));
  document.body.appendChild(toast);

  function say(text, ok) {
    toast.textContent = text;
    toast.className = "toast show" + (ok === false ? " err" : "");
    clearTimeout(say.t);
    say.t = setTimeout(function () { toast.className = "toast"; }, 2800);
  }

  function db() {
    return new Promise(function (resolve, reject) {
      var r = indexedDB.open("flow", 1);
      r.onupgradeneeded = function () { r.result.createObjectStore("handles"); };
      r.onsuccess = function () { resolve(r.result); };
      r.onerror = function () { reject(r.error); };
    });
  }
  function stored() {
    return db().then(function (d) {
      return new Promise(function (resolve) {
        var g = d.transaction("handles").objectStore("handles").get(TASK);
        g.onsuccess = function () { resolve(g.result || null); };
        g.onerror = function () { resolve(null); };
      });
    })["catch"](function () { return null; });
  }
  function remember(handle) {
    return db().then(function (d) {
      return new Promise(function (resolve) {
        var tx = d.transaction("handles", "readwrite");
        tx.objectStore("handles").put(handle, TASK);
        tx.oncomplete = resolve;
        tx.onerror = resolve;
      });
    });
  }

  function readJson(dir, name) {
    return dir.getFileHandle(name).then(function (f) { return f.getFile(); })
      .then(function (f) { return f.text(); }).then(JSON.parse);
  }
  function verify(handle) {
    return handle.getDirectoryHandle("data").then(function (d) { return readJson(d, "task.json"); })
      .then(function (t) {
        if (t.id !== TASK) throw new Error("다른 작업 폴더예요 (" + t.id + ")");
        return handle;
      });
  }

  var folder = null;
  function connect() {
    return window.showDirectoryPicker({ id: "flow", mode: "readwrite" }).then(verify).then(function (h) {
      folder = h;
      return remember(h);
    }).then(function () { return folder; });
  }
  function ensure() {
    if (folder) return Promise.resolve(folder);
    return stored().then(function (h) {
      if (!h) return connect();
      return h.requestPermission({ mode: "readwrite" }).then(function (p) {
        if (p !== "granted") throw new Error("폴더 수정을 허용하지 않았어요");
        folder = h;
        return h;
      });
    });
  }

  function inbox(h) {
    return h.getDirectoryHandle("data").then(function (d) {
      return readJson(d, "inbox.json")["catch"](function () { return { entries: [] }; });
    });
  }
  function writeInbox(h, data) {
    return h.getDirectoryHandle("data").then(function (d) { return d.getFileHandle("inbox.json", { create: true }); })
      .then(function (f) { return f.createWritable(); })
      .then(function (w) { return w.write(JSON.stringify(data, null, 2) + "\n").then(function () { return w.close(); }); });
  }
  function same(a, b) {
    return a.type === b.type && (a.type === "check" ? a.file === b.file && a.key === b.key
      : a.round === b.round && a.question === b.question);
  }
  function push(entries) {
    return ensure().then(function (h) {
      return inbox(h).then(function (box) {
        entries.forEach(function (e) {
          e.at = new Date().toISOString();
          box.entries = box.entries.filter(function (x) { return !same(x, e); });
          box.entries.push(e);
        });
        return writeInbox(h, box).then(function () { return box; });
      });
    });
  }

  function overlay(box) {
    document.querySelectorAll("li.pending").forEach(function (li) { li.classList.remove("pending"); });
    document.querySelectorAll(".badge.pending").forEach(function (b) { b.remove(); });
    box.entries.forEach(function (e) {
      if (e.type === "check" && e.file === FILE) {
        var input = document.querySelector('[data-check="' + e.key + '"]');
        if (input) { input.checked = !!e.done; input.closest("li").classList.add("pending"); }
      }
      if (e.type === "answer" && FILE === "03-grill.html") {
        var form = document.querySelector('.round-form[data-round="' + e.round + '"]');
        var q = form && form.querySelector('.q[data-q="' + e.question + '"]');
        if (!q) return;
        var r = q.querySelector('input[type=radio][value="' + e.choice + '"]');
        if (r) r.checked = true;
        q.querySelector("[data-note]").value = e.note || "";
        q.querySelector("[data-follow]").value = e.followUp || "";
        if (!form.querySelector(".badge.pending")) {
          var b = document.createElement("span");
          b.className = "badge pending";
          b.textContent = "저장됨 · 반영 대기";
          form.querySelector("h2").appendChild(b);
        }
        var d = form.querySelector("details");
        if (d) d.open = true;
      }
    });
    var n = box.entries.length;
    var nav = document.querySelector(".nav .inbox");
    if (!nav) {
      nav = document.createElement("div");
      nav.className = "inbox";
      var steps = document.querySelector(".nav .steps");
      if (steps) steps.insertAdjacentElement("afterend", nav);
    }
    nav.textContent = n ? "반영 안 된 입력 " + n + "건 — 채팅에 '저장했어'라고 알려 주세요" : "";
    nav.classList.toggle("show", n > 0);
  }

  function showConnected() {
    bar.className = "connect on";
    bar.textContent = "폴더 연결됨 · 체크와 답은 data/inbox.json에 저장돼요";
  }
  function showButton(label) {
    bar.className = "connect";
    bar.innerHTML = "";
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.addEventListener("click", function () {
      ensure().then(function (h) { showConnected(); return inbox(h); }).then(overlay)
        ["catch"](function (e) { say(e.message, false); });
    });
    bar.appendChild(b);
    bar.appendChild(document.createTextNode("체크와 답을 저장하려면 이 작업 폴더(" + TASK + ")를 한 번 연결해 주세요"));
  }

  if (!supported) {
    bar.className = "connect off";
    bar.textContent = hasInputs
      ? "이 브라우저에서는 화면에서 저장할 수 없어요(크롬 · 엣지 · Arc에서 돼요). 체크와 답은 채팅으로 알려 주세요."
      : "읽기 전용으로 보고 있어요.";
    document.querySelectorAll("[data-check], .round-form input, .round-form textarea, .round-form button").forEach(function (e) { e.disabled = true; });
    return;
  }

  stored().then(function (h) {
    if (!h) { showButton("폴더 연결"); return; }
    return h.queryPermission({ mode: "readwrite" }).then(function (p) {
      if (p === "granted") { folder = h; showConnected(); return inbox(h).then(overlay); }
      showButton("폴더 다시 연결");
    });
  });

  document.addEventListener("change", function (e) {
    var key = e.target.dataset && e.target.dataset.check;
    if (!key) return;
    var done = e.target.checked;
    push([{ type: "check", file: FILE, key: key, done: done }]).then(function (box) {
      showConnected();
      overlay(box);
      say("저장했어요 · 채팅에 '저장했어'라고 하면 문서에 반영돼요");
    })["catch"](function (err) {
      e.target.checked = !done;
      say("저장하지 못했어요: " + err.message, false);
    });
  });

  document.addEventListener("submit", function (e) {
    var form = e.target.closest && e.target.closest(".round-form");
    if (!form) return;
    e.preventDefault();
    var entries = [];
    form.querySelectorAll(".q[data-q]").forEach(function (q) {
      var c = q.querySelector("input[type=radio]:checked");
      var note = q.querySelector("[data-note]").value.trim();
      var follow = q.querySelector("[data-follow]").value.trim();
      if (!c && !note && !follow) return;
      entries.push({ type: "answer", round: form.dataset.round, question: q.dataset.q,
        choice: c ? c.value : "", note: note, followUp: follow });
    });
    if (!entries.length) { say("고른 답이 없어요", false); return; }
    push(entries).then(function (box) {
      showConnected();
      overlay(box);
      say("저장했어요 · 채팅에 '저장했어'라고 알려 주세요");
    })["catch"](function (err) { say("저장하지 못했어요: " + err.message, false); });
  });
})();
