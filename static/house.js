/* Домик Чик-чика: рисуем комнату (SVG 360x230) из купленных вещей и превью каждой вещи */
(function () {
  'use strict';
  var W = 360, H = 230, WALL_H = 150;
  function rect(x, y, w, h, f, extra) { return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" fill="' + f + '"' + (extra || '') + '/>'; }
  function wallFill(c) { return rect(0, 0, W, WALL_H, c); }
  function stars() { var o = '', p = [[30, 30], [90, 80], [150, 20], [220, 60], [300, 30], [330, 100], [60, 120], [270, 120]]; p.forEach(function (q) { o += '<path transform="translate(' + q[0] + ' ' + q[1] + ') scale(7)" d="M0 -1 L.29 -.4 L.95 -.3 L.47 .15 L.59 .8 L0 .5 L-.59 .8 L-.47 .15 L-.95 -.3 L-.29 -.4Z" fill="#FFD54F"/>'; }); return o; }
  function planks(c, line) { var o = rect(0, WALL_H, W, H - WALL_H, c); for (var y = WALL_H + 20; y < H; y += 20) o += '<path d="M0 ' + y + ' H' + W + '" stroke="' + line + '" stroke-width="2"/>'; for (var x = 40; x < W; x += 80) o += '<path d="M' + x + ' ' + WALL_H + ' V' + H + '" stroke="' + line + '" stroke-width="1.2" opacity=".5"/>'; return o; }
  function win(sky, extra) { return '<rect x="130" y="28" width="100" height="72" rx="6" fill="' + sky + '" stroke="#8A6B4A" stroke-width="6"/>' + (extra || '') + '<path d="M180 28 V100 M130 64 H230" stroke="#8A6B4A" stroke-width="4"/>'; }
  function frame(x, y, w, h, inner) { return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="3" fill="#fff" stroke="#8A6B4A" stroke-width="4"/>' + inner; }

  var ART = {
    'wall-cream': wallFill('#FFF3D6'), 'wall-blue': wallFill('#CFE8FF'), 'wall-pink': wallFill('#FFDDEA'), 'wall-green': wallFill('#D6F5DD'),
    'wall-stars': wallFill('#2F2A6B') + stars(),
    'floor-wood': planks('#E0B073', '#C28F4F'), 'floor-carpet': rect(0, WALL_H, W, H - WALL_H, '#B9A4F5') + '<path d="M0 ' + (WALL_H + 3) + ' H' + W + '" stroke="#9A82E8" stroke-width="4"/>',
    'floor-grass': rect(0, WALL_H, W, H - WALL_H, '#8EDB8A') + [20, 70, 120, 190, 250, 310].map(function (x, i) { return '<path d="M' + x + ' ' + (190 + (i % 3) * 14) + ' l3 -9 l3 9 l3 -9 l3 9" stroke="#4FB35A" stroke-width="2" fill="none"/>'; }).join(''),
    'win-day': win('#9FD8FF', '<ellipse cx="160" cy="50" rx="16" ry="8" fill="#fff"/><ellipse cx="205" cy="82" rx="14" ry="7" fill="#fff"/>'),
    'win-night': win('#2B2A6A', '<circle cx="155" cy="50" r="12" fill="#FFE98A"/><circle cx="153" cy="47" r="12" fill="#2B2A6A"/><circle cx="205" cy="45" r="2" fill="#fff"/><circle cx="210" cy="80" r="2" fill="#fff"/><circle cx="190" cy="85" r="1.5" fill="#fff"/>'),
    'win-rainbow': win('#BFE6FF', ['#E8454B', '#FF9F1C', '#FFD54F', '#4FBF6B', '#3D7BFF'].map(function (c, i) { return '<path d="M' + (140 + i * 4) + ' 98 A' + (40 - i * 4) + ' ' + (40 - i * 4) + ' 0 0 1 ' + (220 - i * 4) + ' 98" stroke="' + c + '" stroke-width="4" fill="none"/>'; }).join('')),
    'bed-small': '<rect x="14" y="130" width="100" height="40" rx="6" fill="#8A6B4A"/><rect x="18" y="116" width="92" height="30" rx="8" fill="#FF8FB8" stroke="#E4709F" stroke-width="2"/><rect x="18" y="110" width="30" height="20" rx="8" fill="#fff" stroke="#DAD3F2" stroke-width="2"/><rect x="14" y="168" width="8" height="12" fill="#6B4F32"/><rect x="106" y="168" width="8" height="12" fill="#6B4F32"/>',
    'bed-royal': '<rect x="10" y="96" width="108" height="76" rx="6" fill="#8E5AD6"/><rect x="10" y="84" width="108" height="16" rx="8" fill="#FFD54F" stroke="#E8A317" stroke-width="2"/><rect x="16" y="126" width="96" height="40" rx="6" fill="#E8454B" stroke="#C0282F" stroke-width="2"/><rect x="20" y="108" width="34" height="22" rx="8" fill="#fff" stroke="#DAD3F2" stroke-width="2"/><path d="M20 84 l8 -14 l8 10 l8 -12 l8 12 l8 -10 l8 14Z" fill="#FFD54F" stroke="#E8A317" stroke-width="2"/>',
    'rug-round': '<ellipse cx="180" cy="196" rx="70" ry="16" fill="#FF9F1C" stroke="#D9780B" stroke-width="2"/><ellipse cx="180" cy="196" rx="46" ry="9" fill="#FFD54F"/>',
    'rug-star': '<ellipse cx="180" cy="196" rx="76" ry="17" fill="#7C5CFF" stroke="#5A3FD6" stroke-width="2"/><path transform="translate(180 196) scale(26 11)" d="M0 -1 L.29 -.4 L.95 -.3 L.47 .15 L.59 .8 L0 .5 L-.59 .8 L-.47 .15 L-.95 -.3 L-.29 -.4Z" fill="#FFD54F"/>',
    'shelf-books': '<rect x="250" y="54" width="86" height="6" rx="2" fill="#8A6B4A"/>' + [[256, '#E8454B', 26], [268, '#3D7BFF', 22], [279, '#4FBF6B', 28], [292, '#FFD54F', 20], [303, '#8E5AD6', 25]].map(function (b) { return '<rect x="' + b[0] + '" y="' + (54 - b[2]) + '" width="10" height="' + b[2] + '" fill="' + b[1] + '"/>'; }).join('') + '<rect x="318" y="38" width="14" height="16" rx="3" fill="#fff" stroke="#8A6B4A" stroke-width="2"/>',
    'shelf-trophies': '<rect x="250" y="54" width="86" height="6" rx="2" fill="#8A6B4A"/><path d="M262 34 h18 v10 a9 9 0 0 1 -18 0Z M271 53 v-0 M266 54 h10" fill="#FFD54F" stroke="#E8A317" stroke-width="2"/><rect x="264" y="48" width="14" height="6" fill="#E8A317"/><path d="M300 30 l3 7 7 1 -5 5 1 7 -6 -3 -6 3 1 -7 -5 -5 7 -1Z" fill="#FFD54F" stroke="#E8A317" stroke-width="1.5"/><rect x="298" y="52" width="14" height="2" fill="#E8A317"/>',
    'pic-chick': frame(20, 30, 56, 56, '<ellipse cx="48" cy="62" rx="16" ry="16" fill="#FFD54F"/><circle cx="43" cy="58" r="2.5" fill="#3b2a6b"/><circle cx="53" cy="58" r="2.5" fill="#3b2a6b"/><path d="M45 64 L48 68 L51 64Z" fill="#FB8C00"/>'),
    'pic-sun': frame(20, 30, 56, 56, '<rect x="24" y="34" width="48" height="48" fill="#BFE6FF"/><circle cx="48" cy="56" r="12" fill="#FFD54F"/><path d="M24 76 H72 V82 H24Z" fill="#8EDB8A"/>'),
    'pic-rocket': frame(20, 30, 56, 56, '<rect x="24" y="34" width="48" height="48" fill="#2B2A6A"/><path d="M48 40 q10 12 6 30 h-12 q-4 -18 6 -30Z" fill="#fff" stroke="#DAD3F2"/><circle cx="48" cy="54" r="4" fill="#3D7BFF"/><path d="M42 70 l-6 8 h6Z M54 70 l6 8 h-6Z" fill="#E8454B"/>'),
    'lamp-floor': '<rect x="318" y="96" width="4" height="84" fill="#6B4F32"/><path d="M304 98 L336 98 L328 72 L312 72Z" fill="#FFD54F" stroke="#E8A317" stroke-width="2"/><ellipse cx="320" cy="182" rx="14" ry="4" fill="#6B4F32"/>',
    'lamp-ball': '<rect x="318" y="140" width="4" height="40" fill="#6B4F32"/><circle cx="320" cy="128" r="16" fill="#FFF3A8" stroke="#FFD54F" stroke-width="3"/><circle cx="320" cy="128" r="24" fill="#FFF3A8" opacity=".35"/><ellipse cx="320" cy="182" rx="14" ry="4" fill="#6B4F32"/>',
    'plant-pot': '<path d="M240 170 h28 l-4 22 h-20Z" fill="#E07A3F" stroke="#B85A25" stroke-width="2"/><path d="M254 170 q-14 -20 -4 -34 M254 170 q14 -22 6 -36 M254 170 v-40" stroke="#4FBF6B" stroke-width="3" fill="none"/><circle cx="254" cy="128" r="7" fill="#FF8FB8"/><circle cx="250" cy="136" r="5" fill="#FF5D8F"/>',
    'plant-cactus': '<path d="M240 170 h28 l-4 22 h-20Z" fill="#C97B4A" stroke="#9A5A2E" stroke-width="2"/><rect x="247" y="130" width="14" height="40" rx="7" fill="#4FBF6B" stroke="#2F9A4B" stroke-width="2"/><path d="M247 148 h-6 v-10 M261 142 h6 v-10" stroke="#2F9A4B" stroke-width="5" stroke-linecap="round" fill="none"/>',
    'plant-tree': '<path d="M240 172 h28 l-4 20 h-20Z" fill="#E07A3F" stroke="#B85A25" stroke-width="2"/><path d="M254 172 q-2 -34 4 -56" stroke="#8A6B4A" stroke-width="5" fill="none"/><path d="M258 116 q-24 -2 -34 14 q20 -6 34 -4 M258 116 q24 -2 34 14 q-20 -6 -34 -4 M258 116 q-4 -20 -22 -22 q14 10 22 22 M258 116 q4 -20 22 -22 q-14 10 -22 22" fill="#4FBF6B" stroke="#2F9A4B" stroke-width="1.5"/>',
    'toy-ball': '<circle cx="110" cy="192" r="11" fill="#E8454B" stroke="#C0282F" stroke-width="2"/><path d="M99 192 h22 M110 181 v22" stroke="#fff" stroke-width="2"/>',
    'toy-duck': '<ellipse cx="108" cy="194" rx="12" ry="8" fill="#FFD54F" stroke="#E8A317" stroke-width="2"/><circle cx="116" cy="184" r="7" fill="#FFD54F" stroke="#E8A317" stroke-width="2"/><path d="M122 184 l7 2 -7 2Z" fill="#FB8C00"/><circle cx="118" cy="182" r="1.4" fill="#3b2a6b"/>',
    'toy-teddy': '<circle cx="108" cy="196" r="10" fill="#B07A4A"/><circle cx="108" cy="181" r="8" fill="#B07A4A"/><circle cx="102" cy="175" r="3.5" fill="#B07A4A"/><circle cx="114" cy="175" r="3.5" fill="#B07A4A"/><circle cx="105" cy="180" r="1.3" fill="#3b2a6b"/><circle cx="111" cy="180" r="1.3" fill="#3b2a6b"/><ellipse cx="108" cy="184" rx="3" ry="2" fill="#E6C29B"/>'
  };
  var BEHIND = ['wall', 'floor', 'window', 'picture', 'shelf', 'rug', 'bed', 'lamp', 'plant'];
  var FRONT = ['toy'];

  function chickAt(outfit) {
    if (!window.Chick) return '';
    return window.Chick.svg(outfit || {}).replace('<svg class="chick"', '<svg x="150" y="100" width="90" height="90" class="chick"');
  }
  function scene(placed, outfit, withChick) {
    var out = '<svg viewBox="0 0 ' + W + ' ' + H + '" xmlns="http://www.w3.org/2000/svg" class="hs-svg">';
    BEHIND.forEach(function (s) { var k = placed[s]; if (k && ART[k]) out += '<g class="h-' + s + '">' + ART[k] + '</g>'; });
    if (withChick) out += chickAt(outfit);
    FRONT.forEach(function (s) { var k = placed[s]; if (k && ART[k]) out += '<g class="h-' + s + '">' + ART[k] + '</g>'; });
    return out + '</svg>';
  }
  window.House = { scene: scene, ART: ART };

  var host = document.getElementById('house');
  if (!host) return;
  var placed = {}, outfit = {};
  try { placed = JSON.parse(host.dataset.placed || '{}'); outfit = JSON.parse(host.dataset.outfit || '{}'); } catch (e) { /* noop */ }
  var sc = document.getElementById('hs-scene');
  if (sc) sc.innerHTML = scene(placed, outfit, true);
  [].forEach.call(host.querySelectorAll('.hs-thumb'), function (t) {
    var o = { wall: 'wall-cream', floor: 'floor-wood' }; o[t.dataset.slot] = t.dataset.key;
    t.innerHTML = scene(o, outfit, false);
  });
})();
