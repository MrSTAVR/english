/* Чик-чик: рисунок цыплёнка и гардероб (шапки, очки, шарфы, цвет перьев).
   window.Chick.svg(outfit) -> строка <svg>; outfit = {hat, face, neck, color} (ключи предметов). */
(function () {
  'use strict';
  function baseSVG() {
    return '<svg class="chick" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
      '<ellipse cx="60" cy="113" rx="30" ry="5" fill="rgba(90,63,214,.16)"/>' +
      '<g class="c-all">' +
        '<path d="M44 104 L40 114 M44 104 L46 115 M44 104 L52 114" stroke="#FB8C00" stroke-width="4" stroke-linecap="round" fill="none"/>' +
        '<path d="M76 104 L72 114 M76 104 L74 115 M76 104 L82 114" stroke="#FB8C00" stroke-width="4" stroke-linecap="round" fill="none"/>' +
        '<g class="c-wing c-wing-l"><path d="M30 60 Q8 62 10 84 Q24 92 36 80 Z" fill="#FFC947" stroke="#E8A317" stroke-width="2" stroke-linejoin="round"/></g>' +
        '<g class="c-wing c-wing-r"><path d="M90 60 Q112 62 110 84 Q96 92 84 80 Z" fill="#FFC947" stroke="#E8A317" stroke-width="2" stroke-linejoin="round"/></g>' +
        '<ellipse cx="60" cy="72" rx="36" ry="36" fill="#FFD54F" stroke="#F2B21B" stroke-width="2.5"/>' +
        '<ellipse cx="60" cy="86" rx="23" ry="19" fill="#FFF3C4"/>' +
        '<g class="c-crest"><path d="M52 40 Q46 24 56 22 Q58 30 58 38 Z" fill="#FFC947"/>' +
          '<path d="M60 38 Q58 18 66 16 Q68 26 66 38 Z" fill="#FFB300"/>' +
          '<path d="M68 40 Q76 28 82 34 Q76 38 72 42 Z" fill="#FFC947"/></g>' +
        '<ellipse cx="34" cy="70" rx="6" ry="4.2" fill="#FF8FB8" opacity=".6"/>' +
        '<ellipse cx="86" cy="70" rx="6" ry="4.2" fill="#FF8FB8" opacity=".6"/>' +
        '<g class="c-look">' +
          '<g class="eo-l"><circle cx="46" cy="58" r="5.6" fill="#3b2a6b"/><circle cx="48" cy="56" r="1.9" fill="#fff"/></g>' +
          '<g class="eo-r"><circle cx="74" cy="58" r="5.6" fill="#3b2a6b"/><circle cx="76" cy="56" r="1.9" fill="#fff"/></g>' +
          '<path class="ec-l" d="M40 58 Q46 63 52 58" stroke="#3b2a6b" stroke-width="3" fill="none" stroke-linecap="round"/>' +
          '<path class="ec-r" d="M68 58 Q74 63 80 58" stroke="#3b2a6b" stroke-width="3" fill="none" stroke-linecap="round"/>' +
          '<g class="eh"><path d="M40 61 Q46 52 52 61" stroke="#3b2a6b" stroke-width="3.2" fill="none" stroke-linecap="round"/>' +
            '<path d="M68 61 Q74 52 80 61" stroke="#3b2a6b" stroke-width="3.2" fill="none" stroke-linecap="round"/></g>' +
          '<g class="ew"><circle cx="46" cy="58" r="8" fill="#fff" stroke="#3b2a6b" stroke-width="2"/><circle cx="46" cy="58" r="3.6" fill="#3b2a6b"/>' +
            '<circle cx="74" cy="58" r="8" fill="#fff" stroke="#3b2a6b" stroke-width="2"/><circle cx="74" cy="58" r="3.6" fill="#3b2a6b"/></g>' +
          '<g class="ed"><path d="M40 52 L52 64 M52 52 L40 64 M68 52 L80 64 M80 52 L68 64" stroke="#3b2a6b" stroke-width="3" stroke-linecap="round"/></g>' +
          '<g class="brows"><path d="M39 50 L52 46" stroke="#3b2a6b" stroke-width="2.6" stroke-linecap="round"/>' +
            '<path d="M81 50 L68 46" stroke="#3b2a6b" stroke-width="2.6" stroke-linecap="round"/></g>' +
        '</g>' +
        '<path d="M51 66 Q60 62 69 66 L60 77 Z" fill="#FB8C00"/>' +
        '<g class="c-beak-low"><path d="M53 75 Q60 85 67 75 Z" fill="#F57C00"/></g>' +
        '@@OUTFIT@@' +
      '</g>' +
      '<g class="fxs">' +
        '<g transform="translate(94 30)"><path class="fx fx-heart" d="M0 -3 C-6 -9 -12 -1 0 7 C12 -1 6 -9 0 -3Z" fill="#FF5D8F"/></g>' +
        '<g transform="translate(24 24)"><path class="fx fx-heart" d="M0 -3 C-6 -9 -12 -1 0 7 C12 -1 6 -9 0 -3Z" fill="#FF8FB8"/></g>' +
        '<g transform="translate(104 52)"><path class="fx fx-heart" d="M0 -3 C-6 -9 -12 -1 0 7 C12 -1 6 -9 0 -3Z" fill="#FF5D8F"/></g>' +
        '<g class="fx-orbit">' +
          '<path class="fx" d="M60 -2 l2.6 5.6 6 .8 -4.4 4.2 1.1 6 -5.3 -2.9 -5.3 2.9 1.1 -6 -4.4 -4.2 6 -.8Z" fill="#7C5CFF"/>' +
          '<path class="fx" d="M92 36 l2.6 5.6 6 .8 -4.4 4.2 1.1 6 -5.3 -2.9 -5.3 2.9 1.1 -6 -4.4 -4.2 6 -.8Z" fill="#FFD54F"/>' +
          '<path class="fx" d="M26 36 l2.6 5.6 6 .8 -4.4 4.2 1.1 6 -5.3 -2.9 -5.3 2.9 1.1 -6 -4.4 -4.2 6 -.8Z" fill="#FF5D8F"/>' +
        '</g>' +
        '<text class="fx fx-z" x="88" y="40" font-size="15" font-weight="900" fill="#7C5CFF" font-family="Nunito,sans-serif">z</text>' +
        '<text class="fx fx-z" x="96" y="30" font-size="12" font-weight="900" fill="#A58BFF" font-family="Nunito,sans-serif">z</text>' +
        '<text class="fx fx-z" x="102" y="20" font-size="9" font-weight="900" fill="#C9B8FF" font-family="Nunito,sans-serif">z</text>' +
        '<path class="fx fx-sweat" d="M90 40 Q95 48 90 52 Q85 48 90 40Z" fill="#6EC6FF"/>' +
        '<g transform="translate(20 50)"><path class="fx fx-spark" d="M0 -8 L2 -2 L8 0 L2 2 L0 8 L-2 2 L-8 0 L-2 -2Z" fill="#FFD54F"/></g>' +
        '<g transform="translate(100 18)"><path class="fx fx-spark" d="M0 -8 L2 -2 L8 0 L2 2 L0 8 L-2 2 L-8 0 L-2 -2Z" fill="#FF5D8F"/></g>' +
        '<g transform="translate(60 4)"><path class="fx fx-spark" d="M0 -8 L2 -2 L8 0 L2 2 L0 8 L-2 2 L-8 0 L-2 -2Z" fill="#7C5CFF"/></g>' +
      '</g>' +
    '</svg>';
  }


  /* ---------- цвета перьев ---------- */
  var BASE = { main: '#FFD54F', belly: '#FFF3C4', stroke: '#F2B21B', wing: '#FFC947', wingS: '#E8A317', crest1: '#FFC947', crest2: '#FFB300' };
  var PALETTES = {
    'color-yellow': BASE,
    'color-pink':   { main: '#FF9EC4', belly: '#FFE3EE', stroke: '#E4709F', wing: '#FF86B5', wingS: '#D65A8C', crest1: '#FF86B5', crest2: '#F0508F' },
    'color-blue':   { main: '#7EC8FF', belly: '#E2F3FF', stroke: '#4BA3E8', wing: '#5FB6F7', wingS: '#3A8FD0', crest1: '#5FB6F7', crest2: '#2F86D6' },
    'color-green':  { main: '#8EE59B', belly: '#E6FAE9', stroke: '#52BF68', wing: '#6FD883', wingS: '#3FA956', crest1: '#6FD883', crest2: '#2FA04B' },
    'color-purple': { main: '#BBA2FF', belly: '#F0E9FF', stroke: '#8C6BE8', wing: '#A688FA', wingS: '#7554D6', crest1: '#A688FA', crest2: '#6B47E0' },
    'color-white':  { main: '#FFFFFF', belly: '#F4F1FF', stroke: '#C9C2E6', wing: '#F1EEFC', wingS: '#BDB5DE', crest1: '#F1EEFC', crest2: '#DAD3F2' }
  };

  /* ---------- предметы: svg в системе координат цыплёнка 120x120 ---------- */
  var STAR5 = 'M0 -1 L.29 -.4 L.95 -.3 L.47 .15 L.59 .8 L0 .5 L-.59 .8 L-.47 .15 L-.95 -.3 L-.29 -.4Z';
  function starAt(x, y, r, fill) { return '<path transform="translate(' + x + ' ' + y + ') scale(' + r + ')" d="' + STAR5 + '" fill="' + fill + '"/>'; }
  function heartAt(x, y, k, fill) { return '<path transform="translate(' + x + ' ' + y + ') scale(' + k + ')" d="M0 3 C-9 -4 -5 -10 0 -5 C5 -10 9 -4 0 3Z" fill="' + fill + '"/>'; }
  var ART = {
    /* --- шапки --- */
    'hat-cap': '<path d="M40 43 Q41 21 60 21 Q79 21 80 43 Z" fill="#3D7BFF" stroke="#2A5DD0" stroke-width="2"/><path d="M60 21 L60 43" stroke="#2A5DD0" stroke-width="1.5"/><circle cx="60" cy="21" r="3" fill="#2A5DD0"/><path d="M70 41 Q94 37 96 45 Q82 49 69 46 Z" fill="#2A5DD0"/>',
    'hat-wizard': '<path d="M42 43 L60 3 L78 43 Z" fill="#6C4BDB" stroke="#4E32B5" stroke-width="2" stroke-linejoin="round"/><ellipse cx="60" cy="43" rx="28" ry="6" fill="#5738BD" stroke="#4E32B5" stroke-width="2"/><path d="M47 36 Q60 41 73 36" stroke="#FFD54F" stroke-width="3" fill="none"/>' + starAt(58, 22, 6, '#FFD54F') + starAt(66, 33, 4, '#FFF3C4'),
    'hat-crown': '<path d="M41 44 L43 22 L52 32 L60 17 L68 32 L77 22 L79 44 Z" fill="#FFD54F" stroke="#E8A317" stroke-width="2.4" stroke-linejoin="round"/><circle cx="60" cy="36" r="3.2" fill="#FF5D8F"/><circle cx="50" cy="39" r="2.4" fill="#4BA3E8"/><circle cx="70" cy="39" r="2.4" fill="#4BA3E8"/>',
    'hat-party': '<path d="M47 43 L60 5 L73 43 Z" fill="#FF5D8F" stroke="#D63C72" stroke-width="2" stroke-linejoin="round"/><path d="M52 31 L68 31 M49 38 L71 38" stroke="#FFD54F" stroke-width="3"/><circle cx="60" cy="5" r="5" fill="#FFD54F"/>',
    'hat-top': '<ellipse cx="60" cy="41" rx="27" ry="5.5" fill="#2F2B45"/><rect x="45" y="14" width="30" height="27" rx="3" fill="#3B3656"/><ellipse cx="60" cy="14" rx="15" ry="3.5" fill="#4A4468"/><rect x="45" y="30" width="30" height="6" fill="#FF5D8F"/>',
    'hat-chef': '<circle cx="48" cy="26" r="10" fill="#fff" stroke="#DAD3F2" stroke-width="2"/><circle cx="60" cy="20" r="11" fill="#fff" stroke="#DAD3F2" stroke-width="2"/><circle cx="72" cy="26" r="10" fill="#fff" stroke="#DAD3F2" stroke-width="2"/><rect x="46" y="29" width="28" height="14" rx="3" fill="#fff" stroke="#DAD3F2" stroke-width="2"/>',
    'hat-santa': '<path d="M41 44 Q43 17 68 13 Q80 12 82 26 Q72 22 68 29 Q80 35 80 44 Z" fill="#E8454B" stroke="#C0282F" stroke-width="2" stroke-linejoin="round"/><rect x="38" y="38" width="44" height="9" rx="4.5" fill="#fff" stroke="#DAD3F2" stroke-width="1.5"/><circle cx="82" cy="26" r="6" fill="#fff" stroke="#DAD3F2" stroke-width="1.5"/>',
    'hat-grad': '<path d="M46 33 L46 45 Q60 52 74 45 L74 33 Z" fill="#2F2B45"/><path d="M28 29 L60 15 L92 29 L60 43 Z" fill="#3B3656" stroke="#25223A" stroke-width="2" stroke-linejoin="round"/><path d="M88 30 L88 46" stroke="#FFD54F" stroke-width="2.4"/><circle cx="88" cy="48" r="3" fill="#FFD54F"/>',
    'hat-flowers': '<path d="M40 45 Q60 30 80 45" stroke="#4FBF6B" stroke-width="4" fill="none" stroke-linecap="round"/><circle cx="46" cy="40" r="5" fill="#FF8FB8"/><circle cx="46" cy="40" r="1.8" fill="#FFD54F"/><circle cx="60" cy="35" r="5.5" fill="#fff" stroke="#E6DDF5" stroke-width="1"/><circle cx="60" cy="35" r="2" fill="#FFD54F"/><circle cx="74" cy="40" r="5" fill="#B79CFF"/><circle cx="74" cy="40" r="1.8" fill="#FFD54F"/><circle cx="53" cy="36" r="2.2" fill="#FFD54F"/><circle cx="67" cy="36" r="2.2" fill="#FF8FB8"/>',
    'hat-phones': '<path d="M33 62 Q32 26 60 26 Q88 26 87 62" stroke="#4A4468" stroke-width="5" fill="none" stroke-linecap="round"/><rect x="26" y="54" width="12" height="20" rx="6" fill="#7C5CFF" stroke="#5A3FD6" stroke-width="2"/><rect x="82" y="54" width="12" height="20" rx="6" fill="#7C5CFF" stroke="#5A3FD6" stroke-width="2"/>',
    'hat-bunny': '<ellipse cx="49" cy="20" rx="7" ry="19" transform="rotate(-10 49 20)" fill="#FFF3C4" stroke="#F2B21B" stroke-width="2"/><ellipse cx="49" cy="21" rx="3.4" ry="13" transform="rotate(-10 49 21)" fill="#FF8FB8"/><ellipse cx="71" cy="20" rx="7" ry="19" transform="rotate(10 71 20)" fill="#FFF3C4" stroke="#F2B21B" stroke-width="2"/><ellipse cx="71" cy="21" rx="3.4" ry="13" transform="rotate(10 71 21)" fill="#FF8FB8"/>',
    /* --- лицо --- */
    'face-glasses': '<circle cx="46" cy="58" r="10" fill="rgba(190,225,255,.35)" stroke="#5A3FD6" stroke-width="3"/><circle cx="74" cy="58" r="10" fill="rgba(190,225,255,.35)" stroke="#5A3FD6" stroke-width="3"/><path d="M56 57 Q60 54 64 57" stroke="#5A3FD6" stroke-width="3" fill="none"/><path d="M36 56 L29 53 M84 56 L91 53" stroke="#5A3FD6" stroke-width="3" stroke-linecap="round"/>',
    'face-sun': '<path d="M35 52 H57 Q57 68 46 68 Q35 68 35 52Z" fill="#25223A"/><path d="M63 52 H85 Q85 68 74 68 Q63 68 63 52Z" fill="#25223A"/><path d="M57 54 H63" stroke="#25223A" stroke-width="3"/><path d="M35 53 L29 50 M85 53 L91 50" stroke="#25223A" stroke-width="3" stroke-linecap="round"/><path d="M40 55 L46 55" stroke="rgba(255,255,255,.5)" stroke-width="2" stroke-linecap="round"/><path d="M68 55 L74 55" stroke="rgba(255,255,255,.5)" stroke-width="2" stroke-linecap="round"/>',
    'face-hearts': heartAt(46, 59, 1.7, 'rgba(255,93,143,.85)') + heartAt(74, 59, 1.7, 'rgba(255,93,143,.85)') + '<path d="M56 56 Q60 53 64 56" stroke="#D63C72" stroke-width="2.6" fill="none"/><path d="M35 55 L29 52 M85 55 L91 52" stroke="#D63C72" stroke-width="2.6" stroke-linecap="round"/>',
    'face-stars': starAt(46, 58, 12, 'rgba(255,213,79,.9)') + starAt(74, 58, 12, 'rgba(255,213,79,.9)') + '<path d="M57 57 Q60 55 63 57" stroke="#E8A317" stroke-width="2.6" fill="none"/>',
    'face-mustache': '<path d="M60 70 Q52 63 42 68 Q47 76 56 72 Q58 71 60 72 Q62 71 64 72 Q73 76 78 68 Q68 63 60 70Z" fill="#6B4A2E" stroke="#4A3220" stroke-width="1.5" stroke-linejoin="round"/>',
    'face-mask': '<path fill-rule="evenodd" d="M32 52 Q60 44 88 52 Q90 66 76 66 Q66 66 62 60 Q60 58 58 60 Q54 66 44 66 Q30 66 32 52Z M46 52 a7.6 7.2 0 1 0 .01 0Z M74 52 a7.6 7.2 0 1 0 .01 0Z" fill="#E8454B"/>',
    /* --- шея --- */
    'neck-bow': '<path d="M60 97 L47 90 L47 104 Z" fill="#E8454B" stroke="#C0282F" stroke-width="1.8" stroke-linejoin="round"/><path d="M60 97 L73 90 L73 104 Z" fill="#E8454B" stroke="#C0282F" stroke-width="1.8" stroke-linejoin="round"/><circle cx="60" cy="97" r="4.4" fill="#FF6F75" stroke="#C0282F" stroke-width="1.6"/>',
    'neck-scarf': '<path d="M33 92 Q60 104 87 92 L89 101 Q60 114 31 101 Z" fill="#7C5CFF" stroke="#5A3FD6" stroke-width="2" stroke-linejoin="round"/><path d="M33 96 Q60 108 87 96 M33 100 Q60 112 87 100" stroke="#FFD54F" stroke-width="2" fill="none" opacity=".9"/><path d="M78 103 L84 118 L72 116 L74 105 Z" fill="#7C5CFF" stroke="#5A3FD6" stroke-width="2" stroke-linejoin="round"/>',
    'neck-medal': '<path d="M50 92 L60 106 L70 92" stroke="#E8454B" stroke-width="5" fill="none" stroke-linejoin="round"/><circle cx="60" cy="108" r="8" fill="#FFD54F" stroke="#E8A317" stroke-width="2.4"/>' + starAt(60, 108, 5, '#E8A317'),
    'neck-lei': '<g>' + [[38, 92], [44, 98], [51, 102], [60, 104], [69, 102], [76, 98], [82, 92]].map(function (p, i) { return '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="4.6" fill="' + ['#FF8FB8', '#FFD54F', '#fff', '#FF5D8F', '#fff', '#FFD54F', '#FF8FB8'][i] + '" stroke="#e6a" stroke-opacity=".3"/>'; }).join('') + '</g>',
    'neck-bandana': '<path d="M34 92 Q60 102 86 92 L60 116 Z" fill="#E8454B" stroke="#C0282F" stroke-width="2" stroke-linejoin="round"/><circle cx="52" cy="98" r="1.7" fill="#fff"/><circle cx="68" cy="98" r="1.7" fill="#fff"/><circle cx="60" cy="106" r="1.7" fill="#fff"/><circle cx="60" cy="98" r="1.7" fill="#fff"/>',
    'neck-tie': '<path d="M60 94 L54 99 L60 118 L66 99 Z" fill="#3D7BFF" stroke="#2A5DD0" stroke-width="1.8" stroke-linejoin="round"/><path d="M54 94 L66 94 L60 99 Z" fill="#2A5DD0"/>'
  };
  var ORDER = ['hat', 'face', 'neck'];

  function svg(outfit) {
    outfit = outfit || {};
    var out = '';
    ORDER.forEach(function (slot) { var k = outfit[slot]; if (k && ART[k]) out += '<g class="o-' + slot + '">' + ART[k] + '</g>'; });
    var s = baseSVG(), cut = s.indexOf('<g class="fxs">');
    var body = s.slice(0, cut), tail = s.slice(cut), pal = PALETTES[outfit.color];
    if (pal && pal !== BASE) {
      Object.keys(BASE).forEach(function (k) { body = body.split(BASE[k]).join(pal[k]); });
    }
    s = (body + tail).replace('@@OUTFIT@@', out);
    return s;
  }
  window.Chick = { svg: svg, ART: ART, PALETTES: PALETTES };
})();
