// ==================== 字体变体（繁/简）切换 ====================
// 默认显示简体
const Variant = {
  current: 'sim',  // 'sim' | 'trad'
  _subs: [],
  /**
   * 注册一个订阅者，回调签名：function(newVariant)
   */
  onChange(fn) {
    this._subs.push(fn);
  },
  set(v) {
    if (v !== 'sim' && v !== 'trad') return;
    if (v === this.current) return;
    this.current = v;
    this._subs.forEach(fn => {
      try { fn(v); } catch (e) { console.error('[Variant] subscriber error:', e); }
    });
    this._updateToggleUI();
  },
  toggle() {
    this.set(this.current === 'sim' ? 'trad' : 'sim');
  },
  /**
   * 根据当前变体返回字符串：'sim' 时返回简体，'trad' 时返回原文
   */
  apply(s) {
    if (s == null) return s;
    if (this.current === 'sim') return t2s(s);
    // 'trad' 模式：对原文（已经是繁体的）直接返回；如调用方传入简，也转回繁
    if (this.current === 'trad' && window.s2t && s && /[\u4e00-\u9fff]/.test(s)) {
      // 启发式：原文已是繁体时，s2t 是 no-op；原文是简时，s2t 转繁
      return window.s2t(s);
    }
    return s;
  },
  _updateToggleUI() {
    const btn = document.getElementById('variantToggle');
    if (!btn) return;
    if (this.current === 'sim') {
      btn.classList.add('sim-active');
      btn.classList.remove('trad-active');
      btn.setAttribute('title', '当前：简体（点击切换为繁体）');
    } else {
      btn.classList.add('trad-active');
      btn.classList.remove('sim-active');
      btn.setAttribute('title', '当前：繁体（点击切换为简体）');
    }
  }
};

window.Variant = Variant;
