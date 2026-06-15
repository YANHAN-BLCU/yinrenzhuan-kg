// ==================== 基础：API 地址、路由、工具 ====================

// Prefer explicit ?api= param, fall back to current page origin (works when served by FastAPI).
const API_BASE = (function() {
  var params = new URLSearchParams(window.location.search);
  var explicit = params.get('api');
  if (explicit) return explicit;
  var port = window.location.port || (window.location.protocol === 'https:' ? '443' : '80');
  return window.location.protocol + '//' + window.location.hostname + ':' + port;
})();

// ==================== 视图路由 ====================
const ROUTES = ['home', 'graph', 'qa'];

function getRoute() {
  var hash = window.location.hash.replace(/^#\/?/, '').toLowerCase();
  return ROUTES.indexOf(hash) >= 0 ? hash : 'home';
}

function showView(route) {
  if (ROUTES.indexOf(route) < 0) route = 'home';
  document.querySelectorAll('[data-view]').forEach(function(el) {
    el.hidden = el.dataset.view !== route;
  });
  document.querySelectorAll('.nav-link').forEach(function(a) {
    if (a.dataset.route === route) {
      a.classList.add('active');
    } else {
      a.classList.remove('active');
    }
  });
  window.scrollTo(0, 0);

  // 各页面懒加载
  if (route === 'graph' && typeof window.loadGraph === 'function' && (!graphData || !graphData.nodes || graphData.nodes.length === 0)) {
    window.loadGraph();
  } else if (route === 'graph' && typeof window.refreshGraph === 'function') {
    window.refreshGraph();
  }
}

window.addEventListener('hashchange', function() {
  showView(getRoute());
});

// ==================== 印章背景网格生成 ====================
(function() {
  const grid = document.getElementById('sealGrid');
  if (!grid) return;
  const chars = ['印', '人', '传', '印', '人', '传', '印', '人', '传', '印', '人', '传'];
  for (let i = 0; i < 40; i++) {
    const cell = document.createElement('div');
    cell.className = 'grid-seal';
    cell.textContent = chars[i % chars.length];
    grid.appendChild(cell);
  }
})();

// ==================== Reveal 动画 ====================
const revealObserver = new IntersectionObserver(function(entries) {
  entries.forEach(function(entry) {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
}, { threshold: 0.1 });

function observeReveal() {
  document.querySelectorAll('[data-view]:not([hidden]) .reveal').forEach(function(el) {
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight) {
      el.classList.add('visible');
    } else {
      revealObserver.observe(el);
    }
  });
}

// ==================== 初始化 ====================
window.addEventListener('DOMContentLoaded', function() {
  showView(getRoute());
  observeReveal();
});
