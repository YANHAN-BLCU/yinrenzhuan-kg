// ==================== 知识图谱 ====================
let graphData = { nodes: [], links: [] };
let simulation, svg, g, zoom;
let currentFilter = 'all';
let currentDynasty = '全部';
let currentHighlightedPath = [];
let openDetailNodeName = null;
let hoveredNodeId = null;
let neighborIds = new Set();
let graphLoaded = false;

const DYNASTY_MAP = ['全部', '明', '清', '元', '现代'];

// 印人傳核心人物所处朝代（按 KG 实际节点整理）
// 优先使用后端 RDF 提供的 dynasty 字段；缺失时回退到本映射表
// 多数人物跨明清，按其主要活动时期归类；无法考证者按学派归类
const PERSON_DYNASTY = {
  // 明代核心人物
  '文彭': '明', '文徵明': '明', '何震': '明', '蘇宣': '明', '黃學': '明',
  '梁千秋': '明', '程原': '明', '劉漁仲': '明', '鄭宏祐': '明',
  '金一甫': '明', '陶石公': '明', '江高臣': '明', '程雲來': '明',
  '程與繩': '明', '程樸': '明', '袁籜庵': '明', '張穉恭': '明',
  '吳頌筠': '明',
  // 明末清初
  '程邃': '明', '萬年少': '明', '顧元方': '明', '顧中翰': '明',
  '顧築公': '明', '張風': '明', '張大風': '明',
  // 清代
  '丁敬': '清', '錢陸燦': '清',
};

function getPersonDynasty(name) {
  return PERSON_DYNASTY[name] || null;
}

async function loadGraph() {
  const loading = document.getElementById('graphLoading');
  const error = document.getElementById('graphError');
  if (loading) loading.style.display = 'flex';
  if (error) error.style.display = 'none';

  try {
    const res = await fetch(`${API_BASE}/api/graph`);
    if (!res.ok) throw new Error('API unavailable');

    const graphJson = await res.json();

    if (!graphJson.nodes || graphJson.nodes.length === 0) {
      if (error) {
        error.style.display = 'flex';
        error.querySelector('p').textContent = '暂无图谱数据，请先运行 src/run_pipeline.py 构建知识图谱';
      }
      if (loading) loading.style.display = 'none';
      return;
    }

    graphJson.nodes.forEach(n => {
      if (n.type !== 'school') {
        n.dynasty = n.dynasty || getPersonDynasty(n.id || n.name) || null;
      }
    });

    graphData = graphJson;
    graphLoaded = true;
    renderGraph(graphJson);
    if (loading) loading.style.display = 'none';
    const nc = document.getElementById('graphNodeCount');
    const ec = document.getElementById('graphEdgeCount');
    if (nc) nc.textContent = graphJson.nodes.length + ' 个节点';
    if (ec) ec.textContent = graphJson.links.length + ' 条关系';
  } catch (e) {
    console.error('Graph load error:', e);
    if (error) error.style.display = 'flex';
    if (loading) loading.style.display = 'none';
  }
}

function refreshGraph() {
  // 进入图谱页时如果已加载过，重新触发 filter 应用即可
  if (graphLoaded && g) {
    applyFilter(currentFilter);
  }
}

function renderGraph(data) {
  const container = document.querySelector('.graph-container');
  if (!container) return;
  const width = container.clientWidth;
  const height = container.clientHeight;

  d3.select('#graphSvg').selectAll('*').remove();

  svg = d3.select('#graphSvg')
    .attr('width', width)
    .attr('height', height);

  zoom = d3.zoom()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
    });

  svg.call(zoom);

  g = svg.append('g');

  const nodes = data.nodes.map(n => ({
    id: n.id || n.name,
    name: n.label || n.name,  // 原始（繁体）名，用于内部匹配
    display: () => (window.Variant ? window.Variant.apply(n.label || n.name) : (n.label || n.name)),
    type: n.type || (n.id && n.id.startsWith('school/') ? 'school' : 'person'),
    centrality: n.centrality,
    dynasty: n.dynasty || (n.type === 'school' ? null : getPersonDynasty(n.id || n.name)) || null
  }));

  const links = data.links.map(l => ({
    source: l.source,
    target: l.target,
    type: l.type || 'related'
  }));

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(90).strength(0.5))
    .force('charge', d3.forceManyBody().strength(-220))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide(30));

  // 连线
  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('class', 'link')
    .attr('stroke', d => {
      if (d.type === 'studentOf' || d.type === 'teacherOf') return '#C1392D';
      if (d.type === 'belongsToSchool' || d.type === 'foundedSchool') return '#4A7A6B';
      return '#C67B30';
    })
    .attr('stroke-width', 1.5);

  // 箭头标记
  const defs = svg.append('defs');
  ['#C1392D', '#4A7A6B', '#C67B30'].forEach(color => {
    defs.append('marker')
      .attr('id', 'arrow-' + color.replace('#', ''))
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('fill', color)
      .attr('d', 'M0,-5L10,0L0,5');
  });

  link.attr('marker-end', d => {
    const color = d.type === 'studentOf' || d.type === 'teacherOf' ? 'C1392D'
      : d.type === 'belongsToSchool' || d.type === 'foundedSchool' ? '4A7A6B' : 'C67B30';
    return `url(#arrow-${color})`;
  });

  // 节点
  const node = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('class', 'node')
    .call(drag(simulation))
    .on('click', function(event, d) {
      event.stopPropagation();
      openNodeDetail(d.name, d.type);
    });

  node.append('circle')
    .attr('r', d => d.type === 'school' ? 22 : 16)
    .attr('fill', d => d.type === 'school' ? '#4A7A6B' : '#C1392D')
    .attr('stroke', 'white')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer');

  node.append('text')
    .attr('dy', d => d.type === 'school' ? 36 : 28)
    .attr('text-anchor', 'middle')
    .text(d => d.display())
    .style('font-size', d => d.type === 'school' ? '11px' : '12px');

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  // 悬停邻居高亮 + 双击定位
  node.selectAll('circle')
    .on('mouseenter', function(event, d) {
      d3.select(this).attr('r', d.type === 'school' ? 26 : 20);
      highlightNeighbors(d);
    })
    .on('mouseleave', function(event, d) {
      d3.select(this).attr('r', d.type === 'school' ? 22 : 16);
      clearNeighborHighlight();
    })
    .on('dblclick', function(event, d) {
      event.stopPropagation();
      locateAndHighlightNode(d.name || d.id, d.type);
    });

  applyFilter(currentFilter);
}

// ==================== 变体切换 ====================
// 当繁/简切换时，仅刷新图谱中受变体影响的文字（节点标签、搜索结果、当前打开的详情面板、路径高亮节点）
if (typeof window.Variant !== 'undefined') {
  window.Variant.onChange(() => {
    // 1. 重新渲染节点文字
    if (g) {
      g.selectAll('.node text').text(d => d.display ? d.display() : (d.name || ''));
    }
    // 2. 如果打开了详情面板，重新打开
    if (openDetailNodeName) {
      const type = (graphData.nodes.find(n => (n.id || n.name) === openDetailNodeName) || {}).type || 'person';
      openNodeDetail(openDetailNodeName, type);
    }
    // 3. 重新触发搜索框（如果有内容）
    const searchInput = document.getElementById('graphSearchInput');
    if (searchInput && searchInput.value.trim()) {
      searchInput.dispatchEvent(new Event('input'));
    }
  });
}

function drag(simulation) {
  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }
  function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }
  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
  }
  return d3.drag()
    .on('start', dragstarted)
    .on('drag', dragged)
    .on('end', dragended);
}

function applyFilter(filter) {
  currentFilter = filter;
  if (!g) return;
  document.querySelectorAll('.graph-filter').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === filter);
  });

  g.selectAll('.node').style('display', d => {
    if (filter === 'all') return '';
    if (filter === 'person') return d.type === 'person' ? '' : 'none';
    if (filter === 'school') return d.type === 'school' ? '' : 'none';
    return '';
  });

  const visibleNodeIds = new Set(
    graphData.nodes
      .filter(n => {
        if (filter === 'all') return true;
        if (filter === 'person') return n.type === 'person';
        if (filter === 'school') return n.type === 'school';
        return true;
      })
      .map(n => n.id)
  );

  g.selectAll('.link').style('display', d => {
    if (filter === 'all') return '';
    return visibleNodeIds.has(d.source.id || d.source) && visibleNodeIds.has(d.target.id || d.target) ? '' : 'none';
  });
}

function zoomIn() {
  if (svg && zoom) svg.transition().duration(300).call(zoom.scaleBy, 1.3);
}

function zoomOut() {
  if (svg && zoom) svg.transition().duration(300).call(zoom.scaleBy, 0.7);
}

function resetZoom() {
  if (svg && zoom) svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity);
}

// ==================== 节点详情面板 ====================
function relTypeLabel(type) {
  const map = {
    'teacherOf': '师父',
    'studentOf': '弟子',
    'belongsToSchool': '所属',
    'foundedSchool': '创立',
    'friendOf': '友人',
    'brotherOf': '兄弟',
    'fatherOf': '父亲',
    'sonOf': '儿子',
    'inheritedFrom': '传承',
    'influencedBy': '影响',
  };
  return map[type] || type;
}

function relBadgeClass(type) {
  if (type === 'teacherOf' || type === 'studentOf') return 'rel-badge-teacher';
  if (type === 'belongsToSchool' || type === 'foundedSchool') return 'rel-badge-school';
  if (type === 'friendOf' || type === 'brotherOf') return 'rel-badge-friend';
  return 'rel-badge-other';
}

function closeNodeDetail() {
  const panel = document.getElementById('nodeDetailPanel');
  if (panel) panel.classList.remove('open');
}

async function openNodeDetail(name, type) {
  const panel = document.getElementById('nodeDetailPanel');
  const badge = document.getElementById('nodeDetailBadge');
  const nameEl = document.getElementById('nodeDetailName');
  const content = document.getElementById('nodeDetailContent');
  if (!panel || !badge || !nameEl || !content) return;

  badge.textContent = type === 'school' ? '学派' : '人物';
  badge.className = 'node-detail-badge ' + (type === 'school' ? 'school' : 'person');
  nameEl.textContent = window.Variant ? window.Variant.apply(name) : name;

  content.innerHTML = `
    <div class="node-detail-loading">
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>
  `;
  panel.classList.add('open');

  try {
    let data;
    if (type === 'school') {
      const res = await fetch(`${API_BASE}/api/school/${encodeURIComponent(name)}`);
      data = await res.json();
      renderSchoolDetail(content, name, data);
    } else {
      const [personRes, relRes] = await Promise.all([
        fetch(`${API_BASE}/api/person/${encodeURIComponent(name)}`),
        fetch(`${API_BASE}/api/relations/${encodeURIComponent(name)}`),
      ]);
      const personData = await personRes.json();
      const relData = await relRes.json();
      renderPersonDetail(content, personData, relData);
    }
  } catch (e) {
    content.innerHTML = `<div class="node-detail-empty">无法加载详情，请确保后端服务已启动</div>`;
  }
}

function renderPersonDetail(el, personData, relData) {
  const p = personData;
  const rels = relData.relations || [];
  const V = window.Variant || { apply: (x) => x };
  const v = (s) => V.apply(s);

  const attrs = [];
  if (p.style_name) attrs.push({ label: '字', value: v(p.style_name) });
  if (p.hao) attrs.push({ label: '号', value: v(p.hao) });
  if (p.dynasty) attrs.push({ label: '朝代', value: v(p.dynasty) });
  if (p.native_place) attrs.push({ label: '籍贯', value: v(p.native_place) });
  if (p.birth_year || p.death_year) {
    const years = [p.birth_year, p.death_year].filter(Boolean).join(' – ');
    attrs.push({ label: '生卒', value: years });
  }

  let html = '';

  if (attrs.length > 0) {
    html += `<div class="node-detail-section">
      <div class="node-detail-section-title">基本信息</div>
      <div class="node-detail-attr-grid">`;
    attrs.forEach(a => {
      html += `<div class="node-detail-attr-item">
        <span class="node-detail-attr-label">${a.label}</span>
        <span class="node-detail-attr-value">${a.value}</span>
      </div>`;
    });
    html += `</div></div>`;
  }

  if (p.schools && p.schools.length > 0) {
    html += `<div class="node-detail-section">
      <div class="node-detail-section-title">所属学派</div>
      <div class="node-detail-school-members">
        ${p.schools.map(s => `<span class="node-detail-member-tag" onclick="openNodeDetail('${s}', 'school')">${v(s)}</span>`).join('')}
      </div>
    </div>`;
  }

  if (rels.length > 0) {
    html += `<div class="node-detail-section">
      <div class="node-detail-section-title">人物关系</div>
      <div class="node-detail-rel-list">`;
    rels.forEach(r => {
      html += `<div class="node-detail-rel-item" onclick="openNodeDetail('${r.target}', 'person')">
        <span class="node-detail-rel-badge ${relBadgeClass(r.type)}">${relTypeLabel(r.type)}</span>
        <span class="node-detail-rel-target">${v(r.target)}</span>
      </div>`;
    });
    html += `</div></div>`;
  }

  if (!html) {
    html = `<div class="node-detail-empty">暂无详细信息</div>`;
  }

  el.innerHTML = html;
}

function renderSchoolDetail(el, schoolName, data) {
  const members = data.members || [];
  const V = window.Variant || { apply: (x) => x };
  const v = (s) => V.apply(s);
  let html = '';

  if (members.length > 0) {
    html += `<div class="node-detail-section">
      <div class="node-detail-section-title">成员列表</div>
      <div class="node-detail-school-members">
        ${members.map(m => {
          const displayName = m.name || '';
          return `<span class="node-detail-member-tag" onclick="openNodeDetail('${displayName}', 'person')">${v(displayName)}</span>`;
        }).join('')}
      </div>
    </div>`;
  }

  if (!html) {
    html = `<div class="node-detail-empty">暂无成员信息</div>`;
  }

  el.innerHTML = html;
}

// ================================================================
// 所有依赖 DOM 的事件绑定：等待 DOM 解析完毕后再执行
// 原因：graph.js 加载于 <head> 中，body 尚未解析，
// 直接执行 document.getElementById / querySelectorAll 会返回 null
// ================================================================
document.addEventListener('DOMContentLoaded', function() {

// 点击图谱空白处关闭面板
if (typeof d3 !== 'undefined') {
  d3.select('#graphSvg').on('click', function(event) {
    if (event.target.tagName === 'svg') {
      closeNodeDetail();
    }
  });
}

// 筛选按钮
document.querySelectorAll('.graph-filter').forEach(btn => {
  btn.addEventListener('click', () => applyFilter(btn.dataset.filter));
});

// ==================== 时代过滤 ====================
const dynastySlider = document.getElementById('dynastySlider');
if (dynastySlider) {
  dynastySlider.addEventListener('input', function () {
    currentDynasty = DYNASTY_MAP[this.value];
    const lbl = document.getElementById('dynastyLabel');
    if (lbl) lbl.textContent = currentDynasty;
    applyDynastyFilter(currentDynasty);
  });
}

function applyDynastyFilter(dynasty) {
  if (!graphData.nodes.length || !g) return;

  // 直接基于 graphData.nodes 判断可见性（节点对象的 id/dynasty 已包含映射值）
  const visibleNodes = new Set();

  graphData.nodes.forEach(n => {
    if (dynasty === '全部') {
      visibleNodes.add(n.id || n.name);
      return;
    }
    // 学派节点始终可见（流派跨朝代存在）
    if (n.type === 'school') {
      visibleNodes.add(n.id || n.name);
      return;
    }
    // 人物节点：仅当有 dynasty 字段且与当前朝代匹配时可见
    // 若无 dynasty 字段（未知），保持可见（宁多勿漏）
    if (!n.dynasty) {
      visibleNodes.add(n.id || n.name);
      return;
    }
    if (n.dynasty === dynasty) {
      visibleNodes.add(n.id || n.name);
    }
  });

  g.selectAll('.node')
    .style('display', d => visibleNodes.has(d.id) ? '' : 'none');

  // 关键修复：line 的 datum d 是 renderGraph 中 mapped links 数组里的对象，
  // d3-force 已把 d.source / d.target 改为节点对象引用，直接读 d.source.id 即可
  // 不必再构建 visibleLinks Set（之前用 graphData.links 元素构建的 Set 与 d 不是同一对象，永远不命中）
  g.selectAll('.link')
    .style('display', d => {
      const src = d.source.id || d.source;
      const tgt = d.target.id || d.target;
      return (visibleNodes.has(src) && visibleNodes.has(tgt)) ? '' : 'none';
    });
}

// ==================== 搜索功能 ====================
const searchInput = document.getElementById('graphSearchInput');
const searchResults = document.getElementById('graphSearchResults');

if (searchInput && searchResults) {
  searchInput.addEventListener('input', function () {
    const q = this.value.trim();
    if (q.length < 1) {
      searchResults.style.display = 'none';
      clearAllHighlights();
      return;
    }

    const variant = window.Variant ? window.Variant.current : 'trad';
    // 搜索时同时比对原始（繁）和简体（若当前是简体）
    const qLower = q.toLowerCase();
    const matches = graphData.nodes.filter(n => {
      const orig = n.label || n.name || '';
      const origLower = orig.toLowerCase();
      const idLower = (n.id || '').toLowerCase();
      if (origLower.includes(qLower) || idLower.includes(qLower)) return true;
      if (variant === 'sim' && window.t2s) {
        const simName = window.t2s(orig);
        if (simName.includes(q) || simName.toLowerCase().includes(qLower)) return true;
      }
      return false;
    }).slice(0, 8);

    if (matches.length === 0) {
      searchResults.innerHTML = '<div class="graph-search-item" style="color:var(--text-muted)">无匹配结果</div>';
      searchResults.style.display = 'block';
      return;
    }

    const displayName = (n) => (window.Variant ? window.Variant.apply(n.label || n.name) : (n.label || n.name));
    searchResults.innerHTML = matches.map(n =>
      `<div class="graph-search-item" data-name="${n.label || n.name}" data-type="${n.type || 'person'}">
        ${displayName(n)}<span class="search-type">${n.type === 'school' ? '学派' : '人物'}</span>
      </div>`
    ).join('');
    searchResults.style.display = 'block';

    searchResults.querySelectorAll('.graph-search-item[data-name]').forEach(item => {
      item.addEventListener('click', () => {
        const name = item.dataset.name;
        const type = item.dataset.type;
        searchResults.style.display = 'none';
        searchInput.value = name;
        locateAndHighlightNode(name, type);
      });
    });
  });

  searchInput.addEventListener('blur', () => {
    setTimeout(() => { searchResults.style.display = 'none'; }, 200);
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const first = searchResults.querySelector('.graph-search-item[data-name]');
      if (first) first.click();
    }
    if (e.key === 'Escape') {
      searchResults.style.display = 'none';
      searchInput.value = '';
      clearAllHighlights();
    }
  });
}

function locateAndHighlightNode(name, type) {
  if (!g) return;
  clearAllHighlights();

  const nodeEl = g.selectAll('.node').filter(d => d.name === name || d.id === name);
  if (nodeEl.empty()) return;

  const d = nodeEl.datum();

  const transform = d3.zoomIdentity
    .translate(-d.x + window.innerWidth / 4, -d.y + window.innerHeight / 4)
    .scale(1.5);
  svg.transition().duration(600).call(zoom.transform, transform);

  nodeEl.select('circle')
    .classed('highlighted', true)
    .attr('r', d.type === 'school' ? 28 : 22);

  openNodeDetail(name, type);

  setTimeout(() => {
    nodeEl.select('circle').classed('highlighted', false)
      .attr('r', d.type === 'school' ? 22 : 16);
  }, 3000);
}

// ==================== 悬停邻居高亮 ====================
function highlightNeighbors(d) {
  if (!d || !g) return;
  hoveredNodeId = d.id || d.name;

  neighborIds = new Set();
  graphData.links.forEach(l => {
    const src = l.source.id || l.source;
    const tgt = l.target.id || l.target;
    if (src === hoveredNodeId) neighborIds.add(tgt);
    if (tgt === hoveredNodeId) neighborIds.add(src);
  });
  neighborIds.add(hoveredNodeId);

  g.selectAll('.node').each(function (n) {
    const id = n.id || n.name;
    const el = d3.select(this);
    if (id === hoveredNodeId) return;
    if (!neighborIds.has(id)) {
      el.select('circle').classed('dimmed', true);
      el.select('text').classed('dimmed', true);
    }
  });

  g.selectAll('.link').each(function (l) {
    const src = l.source.id || l.source;
    const tgt = l.target.id || l.target;
    const el = d3.select(this);
    if (src === hoveredNodeId || tgt === hoveredNodeId) return;
    el.classed('dimmed', true);
  });
}

function clearNeighborHighlight() {
  if (!g) return;
  g.selectAll('.node circle').classed('dimmed', false);
  g.selectAll('.node text').classed('dimmed', false);
  g.selectAll('.link').classed('dimmed', false);
  hoveredNodeId = null;
  neighborIds.clear();
}

// ==================== 最短路径 ====================
const pathSearchBtn = document.getElementById('pathSearchBtn');
const pathClearBtn = document.getElementById('pathClearBtn');
if (pathSearchBtn) pathSearchBtn.addEventListener('click', searchPath);
if (pathClearBtn) pathClearBtn.addEventListener('click', clearPathHighlight);

const pathNodeA = document.getElementById('pathNodeA');
const pathNodeB = document.getElementById('pathNodeB');
if (pathNodeA) {
  pathNodeA.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') searchPath();
  });
}
if (pathNodeB) {
  pathNodeB.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') searchPath();
  });
}

function searchPath() {
  const aEl = document.getElementById('pathNodeA');
  const bEl = document.getElementById('pathNodeB');
  if (!aEl || !bEl) return;
  const nameA = aEl.value.trim();
  const nameB = bEl.value.trim();
  if (!nameA || !nameB) return;

  const adj = {};
  graphData.nodes.forEach(n => { adj[n.id || n.name] = []; });
  graphData.links.forEach(l => {
    const src = l.source.id || l.source;
    const tgt = l.target.id || l.target;
    if (adj[src]) adj[src].push(tgt);
    if (adj[tgt]) adj[tgt].push(src);
  });

  const path = bfs(adj, nameA, nameB);
  if (path) {
    highlightPath(path);
    aEl.value = '';
    bEl.value = '';
  } else {
    alert(`未找到「${nameA}」与「${nameB}」之间的关联路径`);
  }
}

function bfs(adj, start, end) {
  if (start === end) return [start];
  const queue = [[start]];
  const visited = new Set([start]);
  while (queue.length > 0) {
    const path = queue.shift();
    const current = path[path.length - 1];
    for (const neighbor of (adj[current] || [])) {
      if (neighbor === end) return [...path, neighbor];
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push([...path, neighbor]);
      }
    }
  }
  return null;
}

function highlightPath(path) {
  if (!g) return;
  clearPathHighlight();
  currentHighlightedPath = path;

  const pathSet = new Set(path);

  g.selectAll('.node').each(function (n) {
    const id = n.id || n.name;
    if (pathSet.has(id)) {
      d3.select(this).classed('highlighted-path', true);
    }
  });

  g.selectAll('.link').each(function (l) {
    const src = l.source.id || l.source;
    const tgt = l.target.id || l.target;
    for (let i = 0; i < path.length - 1; i++) {
      if ((src === path[i] && tgt === path[i + 1]) ||
          (src === path[i + 1] && tgt === path[i])) {
        d3.select(this).classed('highlighted-path', true);
        break;
      }
    }
  });

  const pathNodes = g.selectAll('.node').filter(d => pathSet.has(d.id || d.name));
  if (!pathNodes.empty()) {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    pathNodes.each(d => {
      if (d.x < minX) minX = d.x;
      if (d.y < minY) minY = d.y;
      if (d.x > maxX) maxX = d.x;
      if (d.y > maxY) maxY = d.y;
    });
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const transform = d3.zoomIdentity
      .translate(-cx + window.innerWidth / 4, -cy + window.innerHeight / 4)
      .scale(1.2);
    svg.transition().duration(600).call(zoom.transform, transform);
  }
}

function clearPathHighlight() {
  if (!g) return;
  currentHighlightedPath = [];
  g.selectAll('.node').classed('highlighted-path', false);
  g.selectAll('.link').classed('highlighted-path', false);
}

function clearAllHighlights() {
  clearPathHighlight();
  clearNeighborHighlight();
}

// 页面可见时刷新图谱
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) loadGraph();
});

}); // end DOMContentLoaded
