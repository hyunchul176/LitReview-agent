/* 정독 카드 공용 스크립트: 다크모드 토글 · figure 라이트박스(클릭 확대) · 그림 상호참조 점프 */
(function () {
  // ---- 테마 토글 ----
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem('theme', t); } catch (e) {}
    document.querySelectorAll('.theme-toggle').forEach(function (b) {
      b.textContent = (t === 'dark') ? '☀ 라이트 모드' : '☾ 다크 모드';
    });
  }
  document.querySelectorAll('.theme-toggle').forEach(function (b) {
    b.addEventListener('click', function () {
      var cur = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      applyTheme(cur === 'dark' ? 'light' : 'dark');
    });
  });
  applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');

  // ---- 라이트박스 (그림 클릭 확대) ----
  var lb = document.getElementById('lightbox');
  if (lb) {
    var lbImg = lb.querySelector('img');
    var lbCap = lb.querySelector('.lightbox-cap');
    document.querySelectorAll('.paper-figure img').forEach(function (img) {
      img.addEventListener('click', function () {
        lbImg.src = img.src;
        lbCap.textContent = img.getAttribute('alt') || '';
        lb.classList.add('open');
      });
    });
    lb.addEventListener('click', function () { lb.classList.remove('open'); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') lb.classList.remove('open');
    });
  }

  // ---- 그림 상호참조(figref) 클릭 시 해당 그림으로 점프 + 깜빡임 ----
  document.querySelectorAll('a.figref').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = a.getAttribute('href');
      if (!id || id[0] !== '#') return;
      var fig = document.querySelector(id);
      if (!fig) return;
      e.preventDefault();
      fig.scrollIntoView({ behavior: 'smooth', block: 'center' });
      fig.classList.remove('fig-flash');
      void fig.offsetWidth;
      fig.classList.add('fig-flash');
    });
  });
})();
