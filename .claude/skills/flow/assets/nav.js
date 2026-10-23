(function () {
  var KEY = "flow-nav-collapsed";
  function read() { try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; } }
  function set(v) { document.body.classList.toggle("collapsed", v); try { localStorage.setItem(KEY, v ? "1" : ""); } catch (e) {} }
  set(read());
  var btn = document.getElementById("navtoggle");
  if (btn) btn.addEventListener("click", function () { set(!document.body.classList.contains("collapsed")); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "[" && !/input|textarea|select/i.test(e.target.tagName)) set(!document.body.classList.contains("collapsed"));
  });
})();
