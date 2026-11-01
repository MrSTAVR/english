// Ферма бабушки Тома: 3D-сцена (three.js, модели Quaternius в /static/farm/), подписи над грядками,
// шторки «Семена», «Заказы», «Амбар», главная кнопка по ситуации. Данные — #fm-data и /api/farm (farm.py).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { clone as skClone } from 'three/addons/utils/SkeletonUtils.js';

const $ = id => document.getElementById(id);
let S = JSON.parse($('fm-data').textContent);
const box = $('fm'), canvas = $('fm-canvas');
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const ico = id => `<svg class="ico" aria-hidden="true"><use href="#${id}"/></svg>`;
const pic = p => window.picHtml ? window.picHtml(p) : esc(p);
const say = t => { if (window.ttsSpeak) window.ttsSpeak(t); };
const CROP = k => S.crops.find(c => c.key === k) || (S.retired || {})[k];   // снятые культуры — только для старых грядок
const csrf = () => (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

// ── сцена ──
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.NoToneMapping;
const scene = new THREE.Scene(); scene.background = new THREE.Color('#9bd967');
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
const cam = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.1, 200);
cam.position.set(30, 32, 30); cam.lookAt(0, 0, 0);
const hemi = new THREE.HemisphereLight('#ffffff', '#9cc66a', 0.6); scene.add(hemi);
const sun = new THREE.DirectionalLight('#fff6e0', 1.7);
sun.position.set(-18, 30, 10); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -22, right: 22, top: 22, bottom: -22, near: 1, far: 100 });
sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.03; scene.add(sun);

function grass() {
  const c = document.createElement('canvas'); c.width = c.height = 512;
  const g = c.getContext('2d'); g.fillStyle = '#7fc44c'; g.fillRect(0, 0, 512, 512);
  let s = 7; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 9000; i++) {
    const x = r() * 512, y = r() * 512;
    g.strokeStyle = r() < .5 ? 'rgba(180,232,110,.8)' : 'rgba(84,150,48,.7)';
    g.lineWidth = 1.2; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (r() - .5) * 3, y - 3 - r() * 4); g.stroke();
  }
  for (let i = 0; i < 90; i++) { g.fillStyle = ['#ffffff', '#fff176', '#ff9ec4'][i % 3]; g.beginPath(); g.arc(r() * 512, r() * 512, 1.8, 0, 7); g.fill(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(8, 8); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const gtex = grass();
const ground = new THREE.Mesh(new THREE.PlaneGeometry(120, 120), new THREE.MeshLambertMaterial({ map: gtex, emissive: '#ffffff', emissiveMap: gtex, emissiveIntensity: .32 }));
ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);

// тёмная тема — вечер на ферме: гасим небо сцены и солнце, а не только CSS-фильтром
const isDark = () => document.documentElement.dataset.theme === 'dark';
function evening() {
  const d = isDark();
  scene.background.set(d ? '#3f5a2c' : '#9bd967');
  sun.intensity = d ? .75 : 1.7; hemi.intensity = d ? .3 : .6;
  ground.material.emissiveIntensity = d ? .1 : .32;
}
new MutationObserver(evening).observe(document.documentElement, { attributeFilter: ['data-theme'] });
evening();

// экран → мир: u — вправо, v — вниз по экрану
const W = (u, v) => { u *= .72; return [(v + u) / 1.4142, (v - u) / 1.4142]; };
const loader = new GLTFLoader(), cache = {};
const MODELS = 2;                                                   // версия моделей: подменённая модель = новый адрес, иначе её держит кэш service worker
const load = n => cache[n] ||= loader.loadAsync(`/static/farm/${n}.glb?v=${MODELS}`);
const mixers = [];
const LEAF = { Green: '#6faf45', DarkGreen: '#4e8b36' };   // листва деревьев и кустов Nature Pack — в палитру фермы
const BARK = '#8a6244';
const NATURE = /^(oak1|birch1|fruittree|pine1|bush1|bush3|bush4)$/;
function prep(obj, name) {
  // у деревьев из Nature Pack материалы очень тёмные (Kd ~0.07) — светлим листву, кору красим в тёплый коричневый
  const NATURE_TREE = NATURE.test(name);
  obj.traverse(o => { if (o.isMesh) { o.castShadow = o.receiveShadow = true;
    let own = false;                                                   // свои материалы помечаем: их можно освобождать, общие — нет
    if (name === 'tomato' || NATURE_TREE) { o.material = Array.isArray(o.material) ? o.material.map(m => m.clone()) : o.material.clone(); own = true; }
    // цвет модели задан в вершинах (COLOR_0), а материал из конвертера остался красным [1,0,0] — красим его в белый.
    // Признак именно красный материал: у коровы тоже есть COLOR_0, но её цвета (белый, чёрный, розовый) заданы материалами
    if (o.geometry.attributes.color && [].concat(o.material).some(m => m.color && m.color.r > .95 && m.color.g < .05 && m.color.b < .05)) {
      o.material = Array.isArray(o.material) ? o.material.map(m => m.clone()) : o.material.clone(); own = true;
      for (const m of [].concat(o.material)) if (m.color && m.color.r > .95 && m.color.g < .05 && m.color.b < .05) { m.vertexColors = true; m.color.setRGB(1, 1, 1); m.needsUpdate = true; } }
    if (own) for (const m of [].concat(o.material)) m.userData.own = true;
    for (const m of [].concat(o.material)) if (m && 'metalness' in m) { m.metalness = 0; m.roughness = Math.max(m.roughness ?? 1, .6);
      if (name === 'tomato' && m.color && m.color.r > m.color.g && m.color.r > m.color.b) { m.color.set('#ff4a36'); m.map = null; }
      if (NATURE_TREE && m.color) { if (LEAF[m.name]) m.color.set(LEAF[m.name]); else if (/wood/i.test(m.name)) m.color.set(BARK); }
      if (name === 'cow' && m.name === 'White') m.color.set('#f4f2ee'); } } });
}
async function put(name, x, z, height, rot = 0, o = {}) {
  const g = await load(name);
  const obj = o.anim ? skClone(g.scene) : g.scene.clone(true);
  prep(obj, name);
  obj.rotation.y = rot; obj.updateMatrixWorld(true);
  let b = new THREE.Box3().setFromObject(obj, !!o.anim); const size = b.getSize(new THREE.Vector3());
  obj.scale.setScalar(o.fitW ? o.fitW / Math.max(size.x, size.z) : height / size.y); obj.updateMatrixWorld(true);
  b = new THREE.Box3().setFromObject(obj, !!o.anim); const c = b.getCenter(new THREE.Vector3());
  obj.position.set(x - c.x, -b.min.y + (o.y0 || 0), z - c.z);
  (o.parent || scene).add(obj);
  if (o.anim && g.animations.length) {
    const mx = new THREE.AnimationMixer(obj);
    const clip = g.animations.find(a => (o.clip || /idle/i).test(a.name)) || g.animations[0];
    const act = mx.clipAction(clip); act.time = Math.random() * clip.duration; act.timeScale = o.speed || 1; act.play(); mixers.push(mx);
    obj.userData.mx = mx; obj.userData.clips = g.animations; obj.userData.act = act;
  }
  return obj;
}
const at = (name, u, v, h, rot, o) => { const [x, z] = W(u, v); return put(name, x, z, h, rot, o); };
const lam = c => new THREE.MeshStandardMaterial({ color: c, roughness: .85, metalness: 0, flatShading: true });
const hitMat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false });
const hits = [];
function hitBox(w, h, d, x, y, z, data) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), hitMat); m.position.set(x, y, z); m.userData = data; scene.add(m); hits.push(m); return m;
}

// ── грядки ──
const BED = 2.2, PLOT_POS = [];
const [bx, bz] = W(0, 3.2);
for (let i = 0; i < 9; i++) PLOT_POS.push([bx + (i % 3 - 1) * (BED + .35), bz + (Math.floor(i / 3) - .5) * (BED + .35)]);
const beds = [];
function bed(i) {
  const [x, z] = PLOT_POS[i], g = new THREE.Group();
  const soil = new THREE.Mesh(new THREE.BoxGeometry(BED, .22, BED), new THREE.MeshLambertMaterial({ color: '#9a6538' }));
  soil.position.set(x, .11, z); soil.castShadow = soil.receiveShadow = true; g.add(soil);
  for (let k = -1; k <= 1; k++) { const row = new THREE.Mesh(new THREE.BoxGeometry(BED - .2, .1, .36), new THREE.MeshLambertMaterial({ color: '#7a4c27' }));
    row.position.set(x, .26, z + k * .62); row.receiveShadow = true; g.add(row); }
  scene.add(g);
  const crop = new THREE.Group(); scene.add(crop);
  hitBox(BED, 1.4, BED, x, .7, z, { kind: 'plot', slot: i });
  return { g, crop, key: '' };
}
const leafGeo = new THREE.IcosahedronGeometry(.16, 0);
const COOP = [-3.9, -3.7], PEN = [5.4, -4], GARDEN = [7.6, 9];   // курятник, загон — над грядками, сад — справа внизу (экранные u, v)             // курятник и загон — над грядками (экранные u, v)
function potato(parent, x, z, stage, seed) {
  let s = seed; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  const g = new THREE.Group(); g.position.set(x, .3, z);
  const mound = new THREE.Mesh(new THREE.SphereGeometry(.21, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), lam('#6b4124'));
  mound.scale.set(1, .45, 1); g.add(mound);
  const k = stage === 'ready' ? 1 : .5, n = stage === 'ready' ? 15 : 5;
  for (let i = 0; i < n; i++) {
    const a = r() * 6.28, rad = (.04 + r() * .15) * k, h = (.08 + r() * .26) * k;
    const leaf = new THREE.Mesh(leafGeo, lam(['#3f8f2f', '#58b03f', '#6cc24a'][Math.floor(r() * 3)]));
    leaf.position.set(Math.cos(a) * rad, .1 + h, Math.sin(a) * rad); leaf.scale.set(1.1 * k, .55 * k, .8 * k); leaf.rotation.set(r(), r() * 6, r()); g.add(leaf);
  }
  if (stage === 'ready') {
    for (let i = 0; i < 3; i++) { const f = new THREE.Mesh(new THREE.IcosahedronGeometry(.035, 0), lam(i % 2 ? '#ffffff' : '#e7d8ff'));
      const a = r() * 6.28; f.position.set(Math.cos(a) * .08, .42 + r() * .06, Math.sin(a) * .08); g.add(f); }
    for (let i = 0; i < 3; i++) { const t = new THREE.Mesh(new THREE.SphereGeometry(.085, 8, 6), lam('#e3b56e'));
      const a = .3 + i * 1.1 + r() * .4; t.scale.set(1.35, .8, 1); t.position.set(Math.cos(a) * .22, .04, Math.sin(a) * .22); t.rotation.y = a; g.add(t); }
  }
  g.traverse(o => { if (o.isMesh) o.castShadow = o.receiveShadow = true; });
  parent.add(g);
}
function fruits(parent, tree, color, blush, n, seed) {
  let s = seed; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  tree.updateMatrixWorld(true);
  const b = new THREE.Box3().setFromObject(tree), size = b.getSize(new THREE.Vector3()), c = b.getCenter(new THREE.Vector3());
  c.y = b.min.y + size.y * .68;
  const ray = new THREE.Raycaster(), meshes = [], spots = []; tree.traverse(o => o.isMesh && meshes.push(o));
  const mat = new THREE.MeshStandardMaterial({ color, roughness: .5, metalness: 0, emissive: blush, emissiveIntensity: .25 });
  const geo = new THREE.SphereGeometry(.09, 12, 10);
  mat.userData.own = true; geo.userData.own = true;                    // созданы для этого дерева — освобождаем при перерисовке
  for (let i = 0; i < 500 && spots.length < n; i++) {
    const a = r() * 6.28, el = -.35 + r() * 1.5;
    const dir = new THREE.Vector3(Math.cos(a) * Math.cos(el), Math.sin(el), Math.sin(a) * Math.cos(el));
    if (dir.x + dir.y + dir.z < .35) continue;
    ray.set(c.clone().addScaledVector(dir, size.x * 1.5), dir.clone().negate());
    const hit = ray.intersectObjects(meshes, false)[0];
    if (!hit || spots.some(p => p.distanceTo(hit.point) < .26)) continue;
    spots.push(hit.point.clone());
    const f = new THREE.Mesh(geo, mat); f.position.copy(hit.point).addScaledVector(dir, .03); f.castShadow = true; parent.add(f);
  }
}
const FRUIT = { apple: ['#e53935', '#5a0d06'], peach: ['#ffa36c', '#ff5a5f'] };
const HEIGHT = { carrot: .75, tomato: .55 };   // на телефоне видно даже помидор
const PIZZA_CROPS = new Set(['wheat', 'mushroom', 'basil', 'oregano', 'lettuce', 'cherry_tomato']);
function drawPizzaCrop(parent, x, z, crop, ready, seed) {
  let s = seed;
  const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  const mat = c => { const m = new THREE.MeshLambertMaterial({ color: c }); m.userData.own = true; return m; };
  const add = (geo, color, px, py, pz, sx = 1, sy = 1, sz = 1) => {
    geo.userData.own = true;
    const m = new THREE.Mesh(geo, mat(color));
    m.position.set(x + px, py, z + pz); m.scale.set(sx, sy, sz);
    m.castShadow = true; parent.add(m); return m;
  };
  const k = ready ? 1 : .62;
  if (crop === 'wheat') {
    for (let i = 0; i < 9; i++) {
      const dx = (r() - .5) * 1.2, dz = (r() - .5) * 1.1;
      add(new THREE.CylinderGeometry(.025, .035, .85 * k, 5), '#c9a54a', dx, .42 * k, dz);
      add(new THREE.ConeGeometry(.1 * k, .24 * k, 5), '#e3c05d', dx, .95 * k, dz);
    }
    return;
  }
  if (crop === 'mushroom') {
    for (let i = 0; i < 7; i++) {
      const dx = (r() - .5) * 1.2, dz = (r() - .5) * 1.1;
      add(new THREE.CylinderGeometry(.06 * k, .08 * k, .24 * k, 6), '#f2e2bd', dx, .14 * k, dz);
      add(new THREE.SphereGeometry(.2 * k, 8, 6), '#b98b6a', dx, .34 * k, dz, 1, .55, 1);
    }
    return;
  }
  if (crop === 'cherry_tomato') {
    for (let i = 0; i < 5; i++) {
      const dx = (r() - .5) * 1.1, dz = (r() - .5) * 1.0;
      add(new THREE.SphereGeometry(.32 * k, 7, 5), '#4e8b36', dx, .34 * k, dz, 1, .8, 1);
      for (let j = 0; j < 3; j++) add(new THREE.SphereGeometry(.09 * k, 7, 5), '#d94a3a', dx + (r() - .5) * .4, .45 * k + r() * .15, dz + (r() - .5) * .4);
    }
    return;
  }
  // базилик, орегано, салат — кустики листьев
  const color = crop === 'lettuce' ? '#5bbb6b' : crop === 'basil' ? '#4caf50' : '#8fa03a';
  for (let i = 0; i < 9; i++) {
    const dx = (r() - .5) * 1.25, dz = (r() - .5) * 1.15;
    add(new THREE.SphereGeometry((crop === 'lettuce' ? .22 : .17) * k, 7, 5), color, dx, .26 * k + r() * .2, dz, 1, .65, 1);
  }
}

async function drawPlot(i, p) {
  const b = beds[i], key = `${p.state}:${p.crop || ''}`;
  if (b.key === key) return;
  b.key = key;
  b.crop.traverse(o => { if (!o.isMesh) return; for (const m of [].concat(o.material)) if (m && m.userData.own) m.dispose();
    if (o.geometry.userData && o.geometry.userData.own) o.geometry.dispose(); });           // геометрия моделей общая с кэшем — её не трогаем
  b.crop.clear();
  const [x, z] = PLOT_POS[i];
  if (p.state === 'empty') return;
  if (p.crop && !CROP(p.crop)) return;                                // культура снята с фермы (кукуруза, тыква) — грядка пустая
  if (p.state === 'planted') {                                        // посажено, ждёт полива: бугорки семян
    for (let a = -1; a <= 1; a++) for (let c = -1; c <= 1; c++) {
      const m = new THREE.Mesh(new THREE.SphereGeometry(.09, 8, 5, 0, 6.3, 0, 1.6), lam('#5e3a1f'));
      m.position.set(x + a * .6, .3, z + c * .62); m.scale.y = .6; b.crop.add(m);
    }
    return;
  }
  const ready = p.state === 'ready';
  if (p.crop === 'potato') { let s = 11 + i * 97; for (let a = -1; a <= 1; a++) for (let c = -1; c <= 1; c++) potato(b.crop, x + a * .6, z + c * .62, p.state, s += 7); return; }
  if (PIZZA_CROPS.has(p.crop)) { drawPizzaCrop(b.crop, x, z, p.crop, ready, 7 + i * 97); return; }
  if (FRUIT[p.crop]) {
    const t = await put('fruittree', x, z, ready ? 2.4 : 1.1, i, { parent: b.crop, y0: .22 });
    if (ready) fruits(b.crop, t, FRUIT[p.crop][0], FRUIT[p.crop][1], 9, 5 + i);
    return;
  }
  const h = HEIGHT[p.crop] * (ready ? 1 : .7);
  const jobs = [];
  for (let a = -1; a <= 1; a++) for (let c = -1; c <= 1; c++) jobs.push(put(p.crop, x + a * .6, z + c * .62, h, (a * 3 + c) * .7, { parent: b.crop, y0: .3 }));
  await Promise.all(jobs);
}

// ── значки над объектами (иконка; подпись — в aria-label и шторке) ──
const labels = [];
function tag(x, y, z, cls, icon, label, onClick, num) {
  const el = document.createElement('button'); el.type = 'button'; el.className = 'fm-tag ' + cls;
  el.innerHTML = (icon[0] === '<' ? icon : ico(icon)) + (num != null ? `<b class="fm-tag-n">${esc(num)}</b>` : '');
  el.setAttribute('aria-label', label); el.title = label;
  el.addEventListener('click', onClick); $('fm-labels').appendChild(el);
  labels.push({ el, p: new THREE.Vector3(x, y, z) });
}
function placeLabels() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  for (const l of labels) {                                          // значок за краем экрана прячем
    const v = l.p.clone().project(cam), x = (v.x + 1) / 2 * w, y = (1 - v.y) / 2 * h;
    l.el.hidden = x < 14 || x > w - 14 || y < 70 || y > h - 70;
    l.el.style.left = x + 'px'; l.el.style.top = y + 'px';
  }
}
function mins(left) { const m = Math.ceil(left / 60); return m <= 1 ? 'через минутку' : m < 60 ? `через ${m} мин` : null; }
function drawLabels() {
  $('fm-labels').innerHTML = ''; labels.length = 0;
  S.plots.forEach((p, i) => {
    const [x, z] = PLOT_POS[i], y = .35;                             // значок — в центре грядки
    if (p.state === 'empty') tag(x, y, z, 'plant', 'o-sprout', 'Посади', () => openSeeds(i));
    else if (p.state === 'planted') tag(x, y, z, 'water', 'o-drop', 'Полей', () => openPlot(i));
    else if (p.state === 'growing') {                                // сколько осталось — числом на значке, не только словами в подписи
      const c = CROP(p.crop), mm = Math.ceil(p.left / 60);
      tag(x, y, z, '', 'o-clock', `Растёт: ${c ? c.ru + ', ' : ''}${mins(p.left) || p.when}`, () => openPlot(i),
          mm < 60 ? mm : Math.round(mm / 60) + ' ч');
    }
    else tag(x, y, z, 'ready', 'o-check', 'Собери урожай', () => openPlot(i));
  });
  if (S.plot_cost) { const [x, z] = PLOT_POS[S.plots.length]; tag(x, .3, z, 'lock', 'o-lock', `Новая грядка — ${S.plot_cost} монеток`, openBuyPlot, S.plot_cost); }
  const animal = (a, x, z, y, lx = x, lz = z) => {                     // lx, lz — где висит замок «ещё не построено»
    if (a.state === 'none') tag(lx, 1.4, lz, 'lock', 'o-lock', a.kind === 'cow' ? 'Коровник' : 'Курятник', () => openAnimal(a.kind));
    else if (a.state === 'hungry') tag(x, y, z, 'water', 'o-grain', 'Покорми', () => openAnimal(a.kind));
    else if (a.state === 'busy') tag(x, y, z, '', 'o-clock', 'Скоро: ' + (mins(a.left) || a.when), () => openAnimal(a.kind));
    else tag(x, y, z, 'ready', 'o-check', 'Собери', () => openAnimal(a.kind));
  };
  const [cx, cz] = W(COOP[0], COOP[1]), [kx, kz] = W(PEN[0], PEN[1]), [lx, lz] = W(PEN[0] - 1.5, PEN[1] - 1.5);
  animal(S.animals.find(a => a.kind === 'chicken'), cx, cz, 3.2);
  animal(S.animals.find(a => a.kind === 'cow'), kx, kz, 2.4, lx, lz);  // без коровы замок — у угла загона, а не в центре
  const [gx, gz] = W(GARDEN[0], GARDEN[1]), gd = S.garden.days;
  tag(gx, gardenH() + .5, gz, gd ? 'ready' : '', 'o-sprout', S.garden.waits && !gd ? 'Сад ждёт тебя' : `Сад: серия ${gd} дн.`,
      () => { location.href = '/student/garden'; }, gd || null);
  placeLabels();
}

// ── камера: вписываем главное в экран ──
const focus = [];                                            // точки, которые должны поместиться на экране
function fit() {
  const w = box.clientWidth, h = box.clientHeight;
  focus.length = 0;                                                  // грядки, что есть (и место под следующую), курятник, загон
  for (const [x, z] of PLOT_POS.slice(0, S.plots.length + (S.plot_cost ? 1 : 0))) for (const dx of [-1, 1]) for (const dz of [-1, 1]) focus.push(new THREE.Vector3(x + dx * BED / 2, 0, z + dz * BED / 2));
  for (const [u, v, y] of [[COOP[0] - 1.4, COOP[1] - .6, 2.8], [PEN[0] + 2.4, PEN[1], 1.2], [PEN[0], PEN[1] - 2, 1.2], [GARDEN[0] + 1.4, GARDEN[1] + 2.4, 0], [GARDEN[0], GARDEN[1] - 1.6, 2]]) { const [x, z] = W(u, v); focus.push(new THREE.Vector3(x, y, z)); }
  if (w >= 700) for (const [u, v, y] of [[0, -10.5, 4], [-5.2, -12, 5.2], [9.4, -9.6, 5]]) {                 // на широком экране — ещё амбар, силос и мельница
    const [x, z] = W(u, v); focus.push(new THREE.Vector3(x, y, z)); }
  renderer.setSize(w, h, false);
  cam.updateMatrixWorld(true);
  const inv = cam.matrixWorldInverse, pts = focus.map(p => p.clone().applyMatrix4(inv));
  let l = Infinity, r = -Infinity, t = -Infinity, b = Infinity;
  for (const p of pts) { l = Math.min(l, p.x); r = Math.max(r, p.x); t = Math.max(t, p.y); b = Math.min(b, p.y); }
  const padTop = w >= 700 ? 2 : 1.4, padBot = 2.2;                   // место под верхние кнопки и нижнюю панель
  t += padTop; b -= padBot;
  let cw = r - l, ch = t - b; const cx = (l + r) / 2, cy = (t + b) / 2, aspect = w / h;
  if (cw / ch > aspect) ch = cw / aspect; else cw = ch * aspect;
  base = { cx, cy, cw, ch };
  applyView();
}
let base = null;
const view = window.farmView = { x: 0, y: 0, zoom: 1 };
function applyView() {
  if (!base) return;
  const lim = Math.max(base.cw, base.ch) * .45;                      // далеко не уехать
  view.x = Math.max(-lim, Math.min(lim, view.x)); view.y = Math.max(-lim, Math.min(lim, view.y));
  view.zoom = Math.max(.75, Math.min(2.2, view.zoom));
  const cx = base.cx + view.x, cy = base.cy + view.y;
  Object.assign(cam, { left: cx - base.cw / 2, right: cx + base.cw / 2, top: cy + base.ch / 2, bottom: cy - base.ch / 2, zoom: view.zoom });
  $('fm-home').hidden = Math.abs(view.x) < .6 && Math.abs(view.y) < .6 && Math.abs(view.zoom - 1) < .06;
  cam.updateProjectionMatrix();
  placeLabels();
}

// ── жизнь сцены: животные бродят, облака плывут, мельница крутится ──
const walkers = [], clouds = [];
let blades = null, pen = null;
const rnd = (a, b) => a + Math.random() * (b - a);
class Walker {                       // подолгу стоит, иногда клюёт/жуёт, потом спокойно идёт в новое место
  constructor(obj, area, o) {
    Object.assign(this, { obj, area, o, state: 'idle', t: rnd(1, o.rest[1]), baseY: obj.position.y, ph: Math.random() * 6.28, peck: rnd(.35, .55) });
    const clips = obj.userData.clips || [];                            // у статичной модели клипов нет — оживляем кодом
    this.proc = !clips.length;
    const find = re => clips.find(c => re.test(c.name));
    this.acts = {};
    for (const k of ['walk', 'idle', 'extra']) if (o[k] && find(o[k])) this.acts[k] = obj.userData.mx.clipAction(find(o[k]));
    this.cur = obj.userData.act;
  }
  play(k, once) {
    const a = this.acts[k]; if (!a || a === this.cur) return;
    a.reset(); a.setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat); a.clampWhenFinished = !!once;
    a.timeScale = k === 'walk' ? this.o.walkScale : .7;
    a.play(); if (this.cur) this.cur.crossFadeTo(a, .35, false); this.cur = a;
  }
  animate(dt) {                                                       // покачивание при ходьбе и «клевок» без скелета
    const p = this.obj.position, r = this.obj.rotation;
    this.ph += dt * (this.state === 'walk' ? 7 : 2);
    if (this.state === 'walk') { p.y = this.baseY + Math.abs(Math.sin(this.ph)) * .05; r.z = Math.sin(this.ph) * .07; r.x *= .85; }
    else if (this.state === 'extra') { const k = 1 - this.t / this.peck; p.y = this.baseY; r.z *= .8; r.x = Math.max(0, Math.sin(k * Math.PI)) * .3; }
    else { p.y += (this.baseY - p.y) * .2; r.z *= .8; r.x *= .7; }
  }
  pick() {
    const A = this.area, p = this.obj.position;
    for (let i = 0; i < 12; i++) {
      const x = A.half ? A.cx + rnd(-A.half, A.half) : A.cx + Math.cos(i * 2.4 + Math.random()) * rnd(.3, A.r);
      const z = A.half ? A.cz + rnd(-A.half, A.half) : A.cz + Math.sin(i * 2.4 + Math.random()) * rnd(.3, A.r);
      if (Math.hypot(x - p.x, z - p.z) > .7) return new THREE.Vector2(x, z);
    }
    return null;
  }
  update(dt) {
    this.t -= dt;
    if (this.state === 'walk') {
      const p = this.obj.position, dx = this.goal.x - p.x, dz = this.goal.y - p.z, d = Math.hypot(dx, dz);
      const want = Math.atan2(dx, dz); let turn = want - this.obj.rotation.y;
      turn = Math.atan2(Math.sin(turn), Math.cos(turn));                 // кратчайший поворот
      this.obj.rotation.y += Math.sign(turn) * Math.min(Math.abs(turn), dt * 2.2);
      const sp = this.o.speed * (this.proc ? .45 + .55 * Math.abs(Math.sin(this.ph)) : 1);   // шаг толчками, а не скольжение
      if (Math.abs(turn) < .5) { const step = Math.min(d, sp * dt); p.x += dx / d * step; p.z += dz / d * step; }
      if (d < .06 || this.t <= 0) { this.state = 'idle'; this.t = rnd(...this.o.rest); this.play('idle'); }
    } else if (this.t <= 0) {
      if (this.state === 'idle' && (this.acts.extra || this.proc) && Math.random() < .4) {
        this.state = 'extra'; this.play('extra', true);
        this.t = this.acts.extra ? this.acts.extra.getClip().duration / .7 : this.peck;   // без скелета — короткий клевок
        if (!this.acts.extra) this.obj.rotation.x = 0;
      } else if ((this.goal = this.pick())) { this.state = 'walk'; this.t = 12; this.play('walk'); }
      else { this.state = 'idle'; this.t = rnd(...this.o.rest); this.play('idle'); }
    }
    if (this.proc) this.animate(dt);
  }
}
function cloud(seed) {                                                 // пухлое облачко из нескольких «камушков»
  let s = seed; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  const g = new THREE.Group(), mat = new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 1, metalness: 0, emissive: '#dbe6f7', emissiveIntensity: .35, transparent: true, opacity: .82 });
  const n = 6 + Math.floor(r() * 3);
  for (let i = 0; i < n; i++) {
    const m = new THREE.Mesh(new THREE.IcosahedronGeometry(.5 + r() * .4, 1), mat);   // гладкое облако, а не «сугроб»
    m.position.set((i - n / 2) * .62 + r() * .2, r() * .35, (r() - .5) * .7); m.scale.y = .72; m.castShadow = true; g.add(m);
  }
  g.scale.setScalar(.95);
  return g;
}
function addClouds() {
  // облака плывут поверху (над амбаром и курятником) — грядки не закрывают; тени скользят по двору
  for (const [k, v, u0, speed] of [[1, -.6, -6, .2], [2, 1.4, 9, .16], [3, -2.2, 15, .18]]) {
    const g = cloud(k * 977 + 13); scene.add(g);
    const c = { g, u: u0, update(dt) {
      this.u += speed * dt; if (this.u > 17) this.u = -17;
      const [x, z] = W(this.u, v); g.position.set(x, 9, z);          // выше крыш — иначе облако читается сугробом
    } };
    c.update(0); clouds.push(c);
  }
}
function spinBlades(mill) {
  mill.traverse(o => {
    if (!o.isMesh || !/Blades/i.test(o.name)) return;
    o.geometry.computeBoundingBox();
    const bb = o.geometry.boundingBox, c = bb.getCenter(new THREE.Vector3()), size = bb.getSize(new THREE.Vector3());
    o.geometry.translate(-c.x, -c.y, -c.z); o.position.add(c.clone().multiply(o.scale).applyQuaternion(o.quaternion));
    const axis = size.x < size.y && size.x < size.z ? new THREE.Vector3(1, 0, 0) : size.y < size.z ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(0, 0, 1);
    o.userData.axis = axis; blades = o;
  });
  return mill;
}

function tall(obj, h) {                                               // растянуть по высоте (забор под размер коровы)
  let b = new THREE.Box3().setFromObject(obj); obj.scale.y *= h / (b.max.y - b.min.y); obj.updateMatrixWorld(true);
  b = new THREE.Box3().setFromObject(obj); obj.position.y -= b.min.y;
}
// сад (серия дней): живая изгородь, дерево растёт вместе с серией; нажатие — страница сада
const gardenH = () => 1 + 2.4 * Math.min(S.garden.grown, S.garden.cap) / S.garden.cap;   // дерево не уменьшается
async function buildGarden() {
  const [gx, gz] = W(GARDEN[0], GARDEN[1]);
  const jobs = [];
  for (let i = 0; i < 9; i++) {
    const a = i / 9 * Math.PI * 2;
    if (Math.abs(a - Math.PI * 1.25) < .4) continue;                   // проход в сад — со стороны грядок
    jobs.push(put('bush3', gx + Math.cos(a) * 2, gz + Math.sin(a) * 2, .7, a));
  }
  jobs.push(put('flowers2', gx + .9, gz - .6, .45), put('flowers2', gx - .8, gz + .7, .45, 2));
  const tree = await put('fruittree', gx, gz, gardenH(), .6);
  await Promise.all(jobs);
  if (S.garden.grown >= 5) fruits(scene, tree, '#e53935', '#5a0d06', Math.min(9, 2 + Math.floor(S.garden.days / 4)), 77);
  hitBox(4.2, 3, 4.2, gx, 1.5, gz, { kind: 'garden' });
}

// ── декорации и постройки ──
async function build() {
  let st = 3;                                                         // камушки-дорожка к амбару
  for (let v = -8.4; v <= -1.6; v += .8) {
    const [x, z] = W(((st = st * 7 % 11) / 11 - .5) * .7, v), r = .27 + (st % 3) * .04;
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r * 1.05, .07, 9), lam('#c9c1ae'));
    m.position.set(x, .035, z); m.rotation.y = st; m.scale.z = .8; m.receiveShadow = true; scene.add(m);
  }
  await Promise.all([
    at('barn', 0, -10.5, 4, Math.PI * .25), at('silo', -5.2, -12, 5.2), at('windmill', 9.4, -9.6, 5, -.6).then(spinBlades),
    at('well', -8.8, -.6, 1.8, .4), at('hay', 2.4, -9.6, .9), at('hay', 3.2, -9.1, .9, .6),
    at('oak1', -11.2, 3.4, 3.2), at('oak1', 9.6, 2.4, 3.4), at('birch1', -3.4, 12.2, 3), at('birch1', 11.8, -3.4, 3.2, 1),
    at('bush1', -2.4, -6.4, .8), at('bush3', 1.6, -8.4, .8), at('flowers2', -9.6, 7.4, .5), at('flowers2', 2.4, 11.6, .5),
    at('coop', COOP[0] - .6, COOP[1] - .6, 2.3, Math.PI * .25),
  ]);
  // ── декор двора: камни, трава, снопы, пни, ягодный куст, ёлки (Ultimate Nature Pack, CC0) ──
  await Promise.all([
    at('rock2', -6.1, -.1, .8, 1.1), at('rock1', -5.4, 8.8, .55, .4), at('rock3', 9.0, 6.4, .5, 2.2), at('rock1', 4.4, 1.2, .4, 1.9),
    at('grass1', -5.6, .2, .5, .8), at('grass2', -3.5, -1.1, .55, 2.4), at('grass1', 4.9, 8.6, .45, 1.6), at('grass2', .6, 8.6, .5, .2),
    at('wheat1', -6.4, -6.8, .9, .3), at('wheat1', -7.2, -6.0, .8, 1.9),
    at('stump1', -1.6, -5.2, .55, .9), at('log1', 2.6, -6.0, .4, .7), at('bush4', -5.8, 10.4, .9, 1.3), at('berries1', 11.4, 4.6, .9, .5),
    at('pine1', -7.6, 11.8, 3.2, .2), at('pine1', 12.2, 9.6, 3.0, 1.4),
  ]);
  const [yx, yz] = W(COOP[0] + 1.3, COOP[1] + .6);                   // дворик у курятника
  for (const [u, v, r] of [[.9, .5, .4], [1.6, -.4, 2], [.2, 1.2, -1]]) {
    const c = await at('hen', COOP[0] + u, COOP[1] + v, 1.0, r);   // модель статичная (Everything Library), ходит с покачиванием
    walkers.push(new Walker(c, { cx: yx, cz: yz, r: 1.5 }, { speed: .42, rest: [3, 8] }));
  }
  const [cx, cz] = W(COOP[0] + .4, COOP[1] + .2); hitBox(3.6, 3, 3.6, cx, 1.5, cz, { kind: 'animal', animal: 'chicken' });
  // загон коровы: пустой забор до покупки коровника выглядел клеткой — прячем, пока коровы нет
  const [px, pz] = W(PEN[0], PEN[1]), half = 2.3, seg = 1.15;
  pen = new THREE.Group(); scene.add(pen);
  for (let t = -half; t < half - .01; t += seg) {
    const parts = await Promise.all([put('fence', px + t + seg / 2, pz - half, 0, 0, { fitW: seg, parent: pen }), put('fence', px + t + seg / 2, pz + half, 0, 0, { fitW: seg, parent: pen }),
      put('fence', px - half, pz + t + seg / 2, 0, Math.PI / 2, { fitW: seg, parent: pen }), put('fence', px + half, pz + t + seg / 2, 0, Math.PI / 2, { fitW: seg, parent: pen })]);
    parts.forEach(f => tall(f, .8));                                   // забор — чуть ниже спины коровы
  }
  await at('hay', PEN[0] + 1.3, PEN[1] - 1.4, .5, .6);                 // сено в загоне: до покупки коровы загон не пустой
  hitBox(half * 2, 2.5, half * 2, px, 1.2, pz, { kind: 'animal', animal: 'cow' });
  for (let i = 0; i < 9; i++) beds.push(bed(i));
  addClouds();
  await buildGarden();

}
let cow = null;
async function sync() {
  $('fm-drops').textContent = S.drops; $('fm-coins').textContent = S.coins;
  const n = S.orders.length; $('fm-orders-n').hidden = !n; $('fm-orders-n').textContent = n;
  beds.forEach((b, i) => { b.g.visible = i < S.plots.length; if (i >= S.plots.length) { b.crop.clear(); b.key = ''; } });
  await Promise.all(S.plots.map((p, i) => drawPlot(i, p)));
  const hasCow = S.animals.find(a => a.kind === 'cow').state !== 'none';
  if (hasCow && !cow) {
    cow = await at('cow', PEN[0], PEN[1], 1.4, 2.1, { anim: true, clip: /\|Idle$/, speed: .8 });   // сначала боком к зрителю
    const [px, pz] = W(PEN[0], PEN[1]);
    walkers.push(new Walker(cow, { cx: px, cz: pz, half: 1.5 }, { walk: /\|WalkSlow$/, idle: /\|Idle$/, speed: .28, rest: [7, 16], walkScale: .8 }));
  }
  drawLabels(); mainButton(); fit();
}

// ── шторка ──
function sheet(title, html) {
  $('fm-sheet-title').textContent = title; $('fm-sheet-body').innerHTML = html; $('fm-sheet').hidden = false;
  $('fm-sheet-title').focus({ preventScroll: true });
}
function closeSheet() { $('fm-sheet').hidden = true; }
$('fm-sheet').addEventListener('click', e => { if (e.target.closest('[data-close]')) closeSheet(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeSheet(); });
function toast(text) { const t = $('fm-toast'); t.textContent = text; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, 2600); }

async function api(action, body) {
  const r = await fetch('/api/farm/' + action, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() }, body: JSON.stringify(body || {}) });
  if (!r.ok) { toast('Что-то пошло не так. Попробуй ещё раз.'); return null; }
  const d = await r.json(); S = d.state; await sync(); return d;
}
async function refresh() { const r = await fetch('/api/farm'); if (r.ok) { S = await r.json(); await sync(); } }

const plural = (n, a, b, c) => n % 10 === 1 && n % 100 !== 11 ? a : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? b : c;
const dropsW = n => `${n} ${plural(n, 'капля', 'капли', 'капель')}`;
const noDrops = need => `<p class="fm-msg bad">Нужно ${dropsW(need)}, а у тебя ${S.drops}. Капли дают за уроки и цель дня!</p>
  <div class="fm-actions"><a class="btn btn-primary" href="/student">К урокам</a></div>`;

function openSeeds(slot) {
  if (slot == null) slot = S.plots.findIndex(p => p.state === 'empty');
  if (slot < 0) { sheet('Семена', '<p class="fm-note">Все грядки заняты. Собери урожай — и сажай снова!</p>' + seedList(null)); return; }
  sheet('Что посадим?', '<p class="fm-note">Посадить — бесплатно. Потом полей грядку — и она начнёт расти.</p>' + seedList(slot));
}
// английское слово и озвучку показываем только после урока, где слово вводится (farm.known)
const enName = (known, en) => known ? `<b lang="en">${esc(en)}</b>` : '';
const sayBtn = (known, en) => known ? `<button type="button" class="fm-say" data-say="${esc(en)}" aria-label="Послушать">${ico('o-sound')}</button>` : '';
function seedList(slot) {
  return '<div class="fm-list">' + S.crops.map(c => c.open
    ? `<div class="fm-row"><span class="fm-pic">${pic(c.pic)}</span><span class="fm-row-text">${enName(c.known, c.en)}<small>${esc(c.ru)} · растёт ${esc(c.grow)} · урожай ${c.yield}</small></span>
       ${sayBtn(c.known, c.en)}
       ${slot != null ? `<button type="button" class="btn btn-small btn-primary" data-plant="${c.key}" data-slot="${slot}">Посадить</button>` : ''}</div>`
    : `<div class="fm-row" aria-disabled="true"><span class="fm-pic">${ico('o-lock')}</span><span class="fm-row-text"><b>???</b><small>откроется после урока «Фрукты и овощи»</small></span></div>`).join('') + '</div>';
}
function openPlot(i) {
  const p = S.plots[i], c = p.crop && CROP(p.crop);
  if (p.state === 'empty') return openSeeds(i);
  const head = `<div class="fm-row"><span class="fm-pic">${pic(c.pic)}</span><span class="fm-row-text">${enName(c.known, c.en)}<small>${esc(c.ru)}</small></span>
    ${sayBtn(c.known, c.en)}</div>`;
  if (p.state === 'planted') sheet('Грядка', head + (S.drops >= S.water
    ? `<div class="fm-actions"><button type="button" class="btn btn-primary" data-act="water" data-slot="${i}">${ico('o-drop')} Полить — ${dropsW(S.water)}</button></div>`
    : noDrops(S.water)));
  else if (p.state === 'growing') sheet('Грядка', head + `<p class="fm-note">Растёт! Поспеет ${esc(mins(p.left) || p.when)}. Урожай не испортится — он подождёт тебя.</p>`);
  else sheet('Грядка', head + `<div class="fm-actions"><button type="button" class="btn btn-primary" data-act="harvest" data-slot="${i}">${ico('o-check')} Собрать урожай</button></div>`);
}
function openAnimal(kind) {
  const a = S.animals.find(x => x.kind === kind);
  const prod = kind === 'chicken' ? 'яйца' : 'молоко';
  const head = `<div class="fm-row"><span class="fm-pic">${pic(a.pic)}</span><span class="fm-row-text">${enName(a.known, a.en)}<small>${esc(a.ru)}</small></span>
    ${sayBtn(a.known, a.en)}</div>`;
  if (a.state === 'none') {
    const can = S.cow.can, enough = S.coins >= S.cow.cost;
    return sheet('Коровник', head + (can
      ? `<p class="fm-note">Корова даёт молоко. Коровник стоит ${S.cow.cost} монеток.</p>` + (enough
        ? `<div class="fm-actions"><button type="button" class="btn btn-primary" data-act="cow">Построить коровник</button></div>`
        : `<p class="fm-msg bad">Пока не хватает: у тебя ${S.coins} монеток. Выполняй заказы!</p>`)
      : '<p class="fm-note">Коровник откроется после урока «Домашние животные».</p>'));
  }
  if (a.state === 'hungry') sheet(a.ru[0].toUpperCase() + a.ru.slice(1), head + (S.drops >= S.feed
    ? `<p class="fm-note">Покорми — и через ${a.minutes < 60 ? a.minutes + ' минут' : a.minutes / 60 + ' часа'} будут ${prod}.</p><div class="fm-actions"><button type="button" class="btn btn-primary" data-act="feed" data-kind="${kind}">Покормить — ${dropsW(S.feed)}</button></div>`
    : noDrops(S.feed)));
  else if (a.state === 'busy') sheet(a.ru[0].toUpperCase() + a.ru.slice(1), head + `<p class="fm-note">Сыта и довольна! ${prod[0].toUpperCase() + prod.slice(1)} будут ${esc(mins(a.left) || a.when)}.</p>`);
  else sheet(a.ru[0].toUpperCase() + a.ru.slice(1), head + `<div class="fm-actions"><button type="button" class="btn btn-primary" data-act="collect" data-kind="${kind}">Собрать ${prod}</button></div>`);
}
function openBuyPlot() {
  sheet('Новая грядка', S.coins >= S.plot_cost
    ? `<p class="fm-note">Ещё одна грядка — ${S.plot_cost} монеток.</p><div class="fm-actions"><button type="button" class="btn btn-primary" data-act="plot">Купить грядку</button></div>`
    : `<p class="fm-note">Ещё одна грядка стоит ${S.plot_cost} монеток, а у тебя ${S.coins}. Выполняй заказы!</p>`);
}
function openBarn() {
  if (!S.barn.length) return sheet('Амбар', '<p class="fm-note">Пока пусто. Собери урожай или яйца — и они появятся здесь.</p>');
  sheet('Амбар', '<div class="fm-list">' + S.barn.map(b => `<div class="fm-row"><span class="fm-pic">${pic(b.pic)}</span>
    <span class="fm-row-text">${enName(S.known[b.item], b.en)}<small>${esc(b.ru)}</small></span><b>×${b.qty}</b>
    ${sayBtn(S.known[b.item], b.en)}</div>`).join('') + '</div>');
}
function openKitchen() {
  const rows = (S.process || []).map(p => {
    const need = p.need.map(n => `${esc(n.ru)} ×${n.qty}`).join(' + ');
    const give = p.give.map(n => `${esc(n.ru)} ×${n.qty}`).join(', ');
    return `<div class="fm-row"><span class="fm-pic">${ico('o-drop')}</span>
      <span class="fm-row-text"><b>${esc(p.ru)}</b><small>${need} → ${give}</small></span>
      <button type="button" class="btn btn-small fm-process-btn ${p.can ? 'btn-primary' : ''}" data-process="${p.key}" ${p.can ? '' : 'disabled'}>${p.can ? 'Сделать' : 'Нет'}</button></div>`;
  }).join('');
  sheet('Кухня', '<p class="fm-note">Переработай урожай в продукты для пиццы. Что не растёт на ферме — лежит в кладовой бесплатно.</p>' +
    (rows ? '<div class="fm-list">' + rows + '</div>' : '<p class="fm-note">Пока нечего готовить.</p>'));
}
const WHO = { Grandma: 'Бабушка', Tom: 'Том', Anna: 'Анна' };
const tries = {};
function openOrders() {
  const w = S.week, pct = Math.min(100, Math.round(100 * w.done / w.goal));
  let html = `<div class="fm-week"><span>Неделя: ${Math.min(w.done, w.goal)} из ${w.goal}</span><span class="fm-week-bar"><i style="width:${pct}%"></i></span></div>`;
  if (!S.orders.length) html += S.slots_today < 3
    ? '<p class="fm-note">Новые заказы приходят за учёбу: за занятие, за сданный урок и за цель дня.</p><div class="fm-actions"><a class="btn btn-primary" href="/student">К урокам</a></div>'
    : '<p class="fm-note">Все заказы на сегодня выполнены. Завтра будут новые!</p>';
  html += S.orders.map(o => `<div class="fm-order" data-order="${o.id}">
    <span class="fm-order-who">${esc(WHO[o.giver] || o.giver)}</span>
    ${o.names
    ? `<div class="fm-order-en"><span lang="en">${esc(o.en)}</span><button type="button" class="fm-say" data-say="${esc(o.en)}" aria-label="Послушать">${ico('o-sound')}</button></div>${uncLine(o.items)}`
    : `<div class="fm-order-en"><span>Просит вот это:</span></div><div class="fm-order-pics">${Object.entries(o.items).map(([k, n]) => `<span>${pic(itemPic(k))}${S.numbers ? '' : ' ' + n}</span>`).join('')}</div>`}
    <div class="fm-order-ru" hidden>${esc(o.ru)}</div>
    <div class="fm-order-foot"><button type="button" class="fm-link" data-tr>перевод</button><span>${ico('i-coin')} ${o.coins}</span>
      <button type="button" class="btn btn-small btn-primary" data-pick="${o.id}">Собрать заказ</button></div></div>`).join('');
  sheet('Заказы', '<div class="fm-list">' + html + '</div>');
}
const itemPic = k => S.pics[k] || '';
// Неисчисляемые товары (молоко): в английской фразе числа нет, поэтому количество показываем значком ×N
const uncLine = items => Object.entries(items).filter(([k]) => (S.uncountable || []).includes(k))
  .map(([k, n]) => `<div class="fm-order-pics"><span>${pic(itemPic(k))} ×${n}</span></div>`).join('');
let picked = {};
function openPick(id) {
  const o = S.orders.find(x => x.id === id); if (!o) return;
  picked = {};
  const items = S.barn.length ? '<div class="fm-pick">' + S.barn.map(b => `<div class="fm-pick-item" data-item="${b.item}"><span class="fm-pic">${pic(b.pic)}</span>
      ${enName(S.known[b.item], b.en)}<span class="fm-step"><button type="button" data-dec="${b.item}" aria-label="Меньше">−</button><b data-n="${b.item}">0</b>
      <button type="button" data-inc="${b.item}" data-max="${b.qty}" aria-label="Больше">+</button><small>из ${b.qty}</small></span></div>`).join('') + '</div>'
    : '<p class="fm-note">В амбаре пока пусто — сначала вырасти урожай.</p>';
  sheet('Собери заказ', `<div class="fm-order"><span class="fm-order-who">${esc(WHO[o.giver] || o.giver)}</span>
    ${o.names ? `<div class="fm-order-en"><span lang="en">${esc(o.en)}</span><button type="button" class="fm-say" data-say="${esc(o.en)}" aria-label="Послушать">${ico('o-sound')}</button></div>${uncLine(o.items)}`
    : `<div class="fm-order-pics">${Object.entries(o.items).map(([k, n]) => `<span>${pic(itemPic(k))}${S.numbers ? '' : ' ' + n}</span>`).join('')}</div>`}
    <div class="fm-order-ru"${(tries[id] || 0) >= 2 ? '' : ' hidden'}>${esc(o.ru)}</div></div>
    <p class="fm-note">Выбери из амбара то, что просят, — и сколько.</p>${items}<div id="fm-pick-msg"></div>
    <div class="fm-actions"><button type="button" class="btn" data-open="orders">Назад</button>
    <button type="button" class="btn btn-primary" data-give="${id}"${S.barn.length ? '' : ' disabled'}>Отдать</button></div>`);
}
async function give(id) {
  const d = await api('order', { id, items: picked });
  if (!d) return;
  if (d.ok) {
    closeSheet();
    toast(`Спасибо! +${d.coins} монеток` + (d.bonus ? ` и +${d.bonus} за неделю!` : ''));
    say('Thank you!');
    return;
  }
  if (d.why === 'gone') { toast('Этот заказ уже выполнен.'); return openOrders(); }
  tries[id] = (tries[id] || 0) + 1;
  openPick(id);
  const keep = picked;
  $('fm-pick-msg').innerHTML = d.why === 'short'
    ? '<p class="fm-msg bad">Всё верно, но в амбаре не хватает. Вырасти ещё!</p>'
    : `<p class="fm-msg bad">Не совсем то. Прочитай заказ ещё раз${tries[id] >= 2 ? ' — вот и перевод' : ''}.</p>`;
  picked = keep;
  Object.entries(picked).forEach(([k, n]) => { const el = document.querySelector(`[data-n="${k}"]`); if (el) { el.textContent = n; el.closest('.fm-pick-item').classList.toggle('on', n > 0); } });
}

// ── нажатия ──
document.addEventListener('click', async e => {
  const t = e.target.closest('button, a'); if (!t || !box.contains(t)) return;
  const d = t.dataset;
  if (d.say) return say(d.say);
  if (d.open === 'seeds') return openSeeds();
  if (d.open === 'orders') return openOrders();
  if (d.open === 'kitchen') return openKitchen();
  if (d.open === 'barn') return openBarn();
  if (d.plant) { closeSheet(); const r = await api('plant', { slot: +d.slot, crop: d.plant }); if (r && !r.ok) toast(r.msg); else if (r) { say(CROP(d.plant).en); openPlot(+d.slot); } return; }
  if (d.process) { const r = await api('process', { key: d.process }); if (!r) return; if (!r.ok) return toast(r.msg); toast(r.msg); openKitchen(); return; }
  if (d.act) {
    const body = d.slot != null ? { slot: +d.slot } : d.kind ? { kind: d.kind } : {};
    const r = await api(d.act, body); if (!r) return;
    closeSheet();
    if (!r.ok) return toast(r.msg);
    if (d.act === 'water') toast('Полито! Растёт…');
    else if (d.act === 'harvest' || d.act === 'collect') toast(`+${r.got} в амбар!`);
    else if (d.act === 'feed') toast('Ням-ням!');
    else if (d.act === 'plot') toast('Новая грядка!');
    else if (d.act === 'cow') toast('Коровник готов! Hello, cow!');
    return;
  }
  if (d.tr != null) { const ru = t.closest('.fm-order').querySelector('.fm-order-ru'); ru.hidden = !ru.hidden; return; }
  if (d.pick) return openPick(+d.pick);
  if (d.inc || d.dec) {
    const k = d.inc || d.dec, max = +(document.querySelector(`[data-inc="${k}"]`).dataset.max);
    picked[k] = Math.max(0, Math.min(max, (picked[k] || 0) + (d.inc ? 1 : -1)));
    if (!picked[k]) delete picked[k];
    document.querySelector(`[data-n="${k}"]`).textContent = picked[k] || 0;
    t.closest('.fm-pick-item').classList.toggle('on', !!picked[k]);
    return;
  }
  if (d.give) return give(+d.give);
});

// главная кнопка — самое полезное действие сейчас
function mainButton() {
  const b = $('fm-main'), ready = S.plots.findIndex(p => p.state === 'ready');
  const ch = S.animals.find(a => a.kind === 'chicken'), cow = S.animals.find(a => a.kind === 'cow');
  const planted = S.plots.findIndex(p => p.state === 'planted'), empty = S.plots.findIndex(p => p.state === 'empty');
  const canOrder = S.orders.some(o => Object.entries(o.items).every(([k, n]) => (S.barn.find(x => x.item === k) || {}).qty >= n));
  let label, run;
  if (ready >= 0) { label = 'Собрать урожай'; run = () => api('harvest', { slot: 'all' }).then(r => r && r.ok && toast(`+${r.got} в амбар!`)); }
  else if (ch.state === 'ready') { label = 'Собрать яйца'; run = () => api('collect', { kind: 'chicken' }).then(r => r && r.ok && toast(`+${r.got} в амбар!`)); }
  else if (cow.state === 'ready') { label = 'Собрать молоко'; run = () => api('collect', { kind: 'cow' }).then(r => r && r.ok && toast(`+${r.got} в амбар!`)); }
  else if (canOrder) { label = 'Выполнить заказ'; run = openOrders; }
  else if (planted >= 0 && S.drops >= S.water) { label = 'Полить грядку'; run = () => api('water', { slot: planted }).then(r => r && r.ok && toast('Полито! Растёт…')); }
  else if (empty >= 0) { label = 'Посадить'; run = () => openSeeds(empty); }
  else if (ch.state === 'hungry' && S.drops >= S.feed) { label = 'Покормить курицу'; run = () => api('feed', { kind: 'chicken' }).then(r => r && r.ok && toast('Ням-ням!')); }
  else if (S.drops < S.water) { label = 'Капли — за уроки'; run = () => { location.href = '/student'; }; }
  else { label = 'Всё растёт!'; run = null; }
  b.textContent = label; b.disabled = !run; b.onclick = run;
}

// нажатие на объект в 3D
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
let down = null, moved = false;
const ptrs = new Map();
const perPx = () => (cam.right - cam.left) / cam.zoom / canvas.clientWidth;
canvas.addEventListener('pointerdown', e => {
  canvas.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]);
  if (ptrs.size === 1) { down = [e.clientX, e.clientY]; moved = false; }
});
canvas.addEventListener('pointermove', e => {
  if (!ptrs.has(e.pointerId)) return;
  const [ox, oy] = ptrs.get(e.pointerId);
  if (ptrs.size === 2) {                                               // щипок
    const [a, b] = [...ptrs.values()], d0 = Math.hypot(a[0] - b[0], a[1] - b[1]);
    ptrs.set(e.pointerId, [e.clientX, e.clientY]);
    const [c, d] = [...ptrs.values()], d1 = Math.hypot(c[0] - d[0], c[1] - d[1]);
    if (d0 > 0) { view.zoom *= d1 / d0; applyView(); }
    moved = true; return;
  }
  ptrs.set(e.pointerId, [e.clientX, e.clientY]);
  if (down && Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 8) moved = true;
  if (moved) { const k = perPx(); view.x -= (e.clientX - ox) * k; view.y += (e.clientY - oy) * k; applyView(); }
});
const lift = e => { ptrs.delete(e.pointerId); };
canvas.addEventListener('pointercancel', lift);
canvas.addEventListener('wheel', e => { e.preventDefault(); view.zoom *= e.deltaY < 0 ? 1.1 : 1 / 1.1; applyView(); }, { passive: false });
canvas.addEventListener('pointerup', e => {
  const was = ptrs.size; lift(e);
  if (!down || moved || was > 1) return;
  const r = canvas.getBoundingClientRect();
  ptr.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
  ray.setFromCamera(ptr, cam);
  const hit = ray.intersectObjects(hits.filter(h => h.userData.kind !== 'plot' || h.userData.slot < S.plots.length), false)[0];
  if (!hit) return;
  const u = hit.object.userData;
  if (u.kind === 'plot') openPlot(u.slot); else if (u.kind === 'garden') location.href = '/student/garden'; else openAnimal(u.animal);
});

// ── запуск ──
const clock = new THREE.Clock();
let alive = true;
function frame() {
  if (!alive) return;
  const dt = Math.min(clock.getDelta(), .05);
  placeLabels(); mixers.forEach(m => m.update(dt));
  walkers.forEach(w => w.update(dt)); clouds.forEach(c => c.update(dt)); if (blades) blades.rotateOnAxis(blades.userData.axis, dt * .5);
  renderer.render(scene, cam);
  requestAnimationFrame(frame);
}
document.addEventListener('visibilitychange', () => { alive = !document.hidden; if (alive) { clock.getDelta(); frame(); refresh(); } });
new ResizeObserver(fit).observe(box);
setInterval(() => {                                                   // обратный отсчёт; поспело — спросим сервер
  let due = false;
  for (const x of [...S.plots, ...S.animals]) if (x.left != null) { x.left -= 1; if (x.left <= 0) due = true; }
  if (due) refresh(); else if (!$('fm-sheet').hidden) return; else drawLabels();
}, 1000);

try {
  await build();
  await sync();
  fit();
  $('fm-loading').hidden = true;
  frame();
} catch (err) {
  $('fm-loading').textContent = 'Не получилось загрузить ферму. Обнови страницу.';
  console.error(err);
}
window.FARM_READY = true;

$('fm-home').addEventListener('click', () => { view.x = 0; view.y = 0; view.zoom = 1; applyView(); });
const movedBtn = $('fm-moved-ok'); if (movedBtn) movedBtn.addEventListener('click', () => { $('fm-moved').hidden = true; });
