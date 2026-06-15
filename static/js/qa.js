// ==================== 知识问答 ====================
async function submitQuestion() {
  const input = document.getElementById('qaInput');
  if (!input) return;
  const question = input.value.trim();
  if (!question) return;

  const resultEl = document.getElementById('qaResult');
  const loadingEl = document.getElementById('qaLoading');
  const submitEl = document.getElementById('qaSubmit');
  if (resultEl) resultEl.style.display = 'none';
  if (loadingEl) loadingEl.style.display = 'flex';
  if (submitEl) submitEl.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/qa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });

    if (!res.ok) throw new Error('QA request failed');
    const data = await res.json();

    showQAResult(data);
  } catch (e) {
    console.error('QA error:', e);
    showQAResult({
      answer: '无法连接到后端服务，请确保 FastAPI 服务已启动（python src/main.py）',
      fallback_used: true
    });
  } finally {
    if (loadingEl) loadingEl.style.display = 'none';
    if (submitEl) submitEl.disabled = false;
  }
}

function showQAResult(data) {
  const resultEl = document.getElementById('qaResult');
  const bodyEl = document.getElementById('qaResultBody');
  const metaEl = document.getElementById('qaResultMeta');
  if (!resultEl || !bodyEl || !metaEl) return;

  const V = window.Variant || { apply: (x) => x };
  const v = (s) => V.apply(s);

  const meta = [];
  if (data.intent) meta.push(`意图: ${v(data.intent)}`);
  if (data.answer_source === 'kg_query') meta.push('知识图谱');
  if (data.sparql) meta.push('SPARQL');
  metaEl.innerHTML = meta.map(m => `<span>${m}</span>`).join('');

  let html = `<p>${v(data.answer) || '暂无答案'}</p>`;

  if (data.entities && data.entities.length > 0) {
    html += `<div style="margin-top:8px;font-size:12px;color:var(--text-muted)">识别实体: ${data.entities.map(v).join('、')}</div>`;
  }

  if (data.sparql) {
    html += `<div style="margin-top:12px;font-size:12px;color:var(--text-muted);font-family:monospace;background:#f5f0e8;padding:8px 12px;border-radius:6px;overflow-x:auto">
      <strong>SPARQL:</strong> ${data.sparql.replace(/\n/g, '<br>').substring(0, 300)}${data.sparql.length > 300 ? '...' : ''}
    </div>`;
  }

  if (data.query_result && data.query_result.results && data.query_result.results.length > 0) {
    const rows = data.query_result.results;
    html += `<div style="margin-top:12px;font-size:13px">
      <strong>查询结果 (${rows.length} 条):</strong>
      <ul style="margin-top:4px;padding-left:18px">`;
    rows.slice(0, 5).forEach(r => {
      const vals = Object.values(r).filter(val => val).map(v).join(' | ');
      if (vals) html += `<li>${vals}</li>`;
    });
    html += '</ul></div>';
  }

  bodyEl.innerHTML = html;
  resultEl.style.display = 'block';
}

function askQuestion(q) {
  const input = document.getElementById('qaInput');
  if (input) {
    input.value = q;
  }
  submitQuestion();
}

const qaInput = document.getElementById('qaInput');
if (qaInput) {
  qaInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitQuestion();
    }
  });
}

// ==================== 变体切换：刷新当前结果 ====================
// 缓存最近一次结果，繁/简切换时直接用缓存重新渲染（无需再请求后端）
if (typeof window.Variant !== 'undefined') {
  window._lastQAResult = null;
  // 拦截全局的 showQAResult（HTML 中的 onclick 写死了 showQAResult）
  const _origShowQAResult = window.showQAResult || showQAResult;
  window.showQAResult = function (data) {
    window._lastQAResult = data;
    _origShowQAResult(data);
  };

  window.Variant.onChange(() => {
    if (window._lastQAResult) {
      _origShowQAResult(window._lastQAResult);
    }
  });
}
