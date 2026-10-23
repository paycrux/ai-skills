(function () {
  function hot(i, scrollFig) {
    document.querySelectorAll(".pin.hot, tr.hot").forEach(function (e) { e.classList.remove("hot"); });
    var p = document.querySelector('.pin[data-i="' + i + '"]'), r = document.querySelector('tr[data-i="' + i + '"]');
    if (!p || !r) return;
    p.classList.add("hot"); r.classList.add("hot");
    var shot = p.closest(".shot");
    if (scrollFig && shot) shot.scrollTop = p.offsetTop - shot.clientHeight / 2;
  }
  document.querySelectorAll("tbody tr[data-i]").forEach(function (r) {
    r.addEventListener("mouseenter", function () { hot(r.dataset.i, true); });
  });
  document.querySelectorAll(".pin").forEach(function (p) {
    p.addEventListener("click", function () {
      document.querySelector('tr[data-i="' + p.dataset.i + '"]').scrollIntoView({ behavior: "smooth", block: "center" });
      hot(p.dataset.i, false);
    });
  });
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting && !document.querySelector("tr.hot:hover")) hot(e.target.dataset.i, true); });
  }, { rootMargin: "-45% 0px -45% 0px" });
  document.querySelectorAll("tbody tr[data-i]").forEach(function (r) { io.observe(r); });
})();
