// ==================== 印章鉴赏卡片 ====================
const sealData = [
  { char: '柴门深处', style: '名章', author: '何震', era: '明代', desc: '明代篆刻宗师何震代表作，线条刚劲挺拔，刀法犀利爽利，印风雄强恣肆，为徽派篆刻开山鼻祖。', img: 'index_card/柴门深处-何震.png' },
  { char: '明月清风我', style: '名章', author: '文彭', era: '明代', desc: '明代文人篆刻鼻祖文彭所刻，印风秀润典雅，笔意含蓄温婉，开创明清文人篆刻之先河。', img: 'index_card/明月清风我-文彭.png' },
  { char: '古驿亭长', style: '名章', author: '陈豫钟', era: '清代', desc: '清代西泠八家之一陈豫钟佳作，篆法工整精妙，线条圆润秀雅，印风端庄清丽，浙派篆刻典范之作。', img: 'index_card/古驿亭长-陈豫钟.png' },
  { char: '家书抵万金', style: '名章', author: '丁敬', era: '清代', desc: '浙派篆刻创始人丁敬所刻，刀法苍劲古拙，篆法朴茂雄健，开清代浙派印风之宗。', img: 'index_card/家书抵万金-丁敬.png' },
  { char: '勿言小大随分有风波', style: '名章', author: '汪关', era: '清代', desc: '明代/清代篆刻家汪关经典作品，刀法精工细腻，线条圆润流畅，印风典雅工稳，为娄东派篆刻代表。', img: 'index_card/勿言小大随分有风波-汪关.png' },
  { char: '停云', style: '名章', author: '文徵明', era: '明代', desc: '明代书画大家文徵明自用印，印风清雅秀逸，篆法简洁端庄，尽显文人雅士风骨。', img: 'index_card/停云-文徵明.png' },
  { char: '伯惠', style: '名章', author: '黄士陵', era: '清代', desc: '晚清黟山派宗师黄士陵所刻，线条挺劲光洁，章法平正疏朗，印风冷峻雅逸，自成一派。', img: 'index_card/伯惠-黄士陵.png' },
  { char: '茶到三分也醉人', style: '名章', author: '程大年', era: '清代', desc: '清代篆刻名家程大年作品，印文意境清雅，刀法稳健自然，尽显文人闲情逸致。', img: 'index_card/茶到三分也醉人-程大年.jpg' },
  { char: '养贤', style: '名章', author: '赵锡绶', era: '清代', desc: '清代篆刻家赵锡绶佳作，章法规整大气，线条浑厚凝练，印风端庄古朴，寓意崇德尚贤。', img: 'index_card/养贤-赵锡绶.png' },
  { char: '周世之印', style: '名章', author: '王常', era: '近现代', desc: '近现代书法篆刻大家王常所刻，篆法古拙厚重，刀法苍劲有力，兼具金石气韵与文人意趣。', img: 'index_card/周世之印-王常.png' },
];

const floatClasses = ['float-a', 'float-b', 'float-c', 'float-a', 'float-b',
                      'float-c', 'float-a', 'float-b', 'float-c', 'float-a'];

const sealPaths = {
  '永': 'M65 30 C45 50 35 80 40 100 C43 110 50 115 55 110 C48 95 50 75 65 60 C70 55 80 60 85 75 C90 90 85 110 80 125 M55 70 C60 65 65 60 65 55 C65 50 60 45 55 40',
  '泰': 'M30 50 Q50 30 75 45 M35 70 Q55 55 70 65 M40 90 Q55 80 65 88 M30 50 L35 110 M75 45 L70 105',
  '安': 'M35 45 Q50 35 65 45 M30 60 Q50 50 70 60 M40 80 L40 105 L60 105 L60 80 M35 95 L65 95',
  '樂': 'M50 25 L50 55 M35 40 L50 55 L65 40 M30 70 Q50 60 70 70 M40 90 L40 110 L60 110 L60 90',
  '利': 'M55 30 L35 110 M30 65 L70 65 M35 95 L55 95',
  '年': 'M30 45 Q50 35 70 45 M35 60 L35 110 M70 60 L70 110 M40 85 L65 85 M30 45 L30 55',
  '福': 'M30 40 Q50 30 70 40 M30 55 Q50 50 70 55 M40 70 L40 105 L60 105 L60 70 M35 85 L65 85',
  '昌': 'M35 40 L35 100 L65 100 L65 40 M40 50 L60 50 M40 70 L60 70 M40 90 L60 90'
};

function createSealSVG(char) {
  const path = sealPaths[char] || `M30 40 Q50 30 70 40 M40 70 L40 100 L60 100 L60 70`;
  return `<svg viewBox="0 0 100 140" xmlns="http://www.w3.org/2000/svg" width="70" height="98">
    <rect x="2" y="2" width="96" height="136" fill="none" stroke="#C1392D" stroke-width="2"/>
    <path d="${path}" fill="none" stroke="#C1392D" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`;
}

function buildSealCards() {
  const grid = document.getElementById('cardsGrid');
  if (!grid) return;

  sealData.forEach((seal, i) => {
    const floatClass = floatClasses[i % floatClasses.length];

    const card = document.createElement('div');
    card.className = 'showcase-card';
    card.style.animationDelay = `${i * 80}ms`;
    card.dataset.index = i;

    card.innerHTML = `
      <div class="showcase-card-inner">
        <div class="showcase-card-face showcase-card-front">
          <div class="front-seal-wrap">
            ${seal.img
              ? `<img src="${seal.img}" alt="${seal.char}" class="front-seal-img" />`
              : createSealSVG(seal.char)
            }
          </div>
          <span class="front-number">${seal.char}</span>
        </div>
        <div class="showcase-card-face showcase-card-back">
          <div class="back-top-bar">
            <span class="back-title">「${seal.char}」</span>
          </div>
          <div class="back-body">
            <div class="back-meta">
              <div class="meta-item">
                <span class="meta-label">Author</span>
                <span class="meta-value">${seal.author}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Era</span>
                <span class="meta-value">${seal.era}</span>
              </div>
            </div>
            <p class="back-desc">${seal.desc}</p>
          </div>
          <div class="back-footer">
            <span class="flip-hint">Click to flip</span>
          </div>
        </div>
      </div>
    `;

    card.classList.add(floatClass);

    card.addEventListener('click', () => {
      card.classList.toggle('flipped');
    });

    grid.appendChild(card);
  });
}

buildSealCards();
