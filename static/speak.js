/* ============================================================
   🎤 Тренировка произношения.
   Браузер слушает микрофон (Web Speech API), превращает речь в
   текст, а мы сравниваем текст с нужным словом. Это проверка
   «тебя поняли?», а не фонетический разбор: если распознано
   именно то слово — произношение достаточно чёткое.
   Звук на наш сервер НЕ отправляется — только оценка (0–3 ⭐).
   ============================================================ */
(function (root) {
  'use strict';

  var SR = root.SpeechRecognition || root.webkitSpeechRecognition;

  var NUMS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
              'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen',
              'nineteen', 'twenty'];
  var TENS = { 30: 'thirty', 40: 'forty', 50: 'fifty', 60: 'sixty', 70: 'seventy', 80: 'eighty', 90: 'ninety', 100: 'one hundred' };
  var CONTR = {
    "i'm": 'i am', "you're": 'you are', "he's": 'he is', "she's": 'she is', "it's": 'it is',
    "we're": 'we are', "they're": 'they are', "what's": 'what is', "that's": 'that is', "let's": 'let us',
    "isn't": 'is not', "aren't": 'are not', "don't": 'do not', "doesn't": 'does not',
    "can't": 'can not', 'cannot': 'can not', "won't": 'will not', "wasn't": 'was not'
  };

  /* слова, которые звучат одинаково: распознаватель выбирает любое из них */
  var HOMO = {};
  [['to', 'too', 'two'], ['no', 'know'], ['write', 'right'], ['see', 'sea'], ['hi', 'high'],
   ['i', 'eye', 'aye'], ['by', 'buy', 'bye'], ['one', 'won'], ['for', 'four', 'fore'], ['eight', 'ate'],
   ['son', 'sun'], ['be', 'bee'], ['you', 'u', 'ewe'], ['are', 'r'], ['why', 'y'], ['hear', 'here'],
   ['there', 'their', "they're"], ['wear', 'where'], ['hole', 'whole'], ['blue', 'blew'], ['red', 'read'],
   ['dear', 'deer'], ['pair', 'pear', 'pare'], ['tail', 'tale'], ['meet', 'meat'], ['bear', 'bare'],
   ['sail', 'sale'], ['plain', 'plane'], ['wait', 'weight'], ['week', 'weak'], ['flower', 'flour'],
   ['night', 'knight'], ['new', 'knew'], ['nose', 'knows'], ['knee', 'nee'], ['wood', 'would'],
   ['its', "it's"], ['our', 'hour'], ['ok', 'okay'], ['mom', 'mum'], ['color', 'colour']
  ].forEach(function (g) { g.forEach(function (w) { HOMO[w] = g[0]; }); });

  function norm(s) {
    s = String(s || '').toLowerCase().replace(/[’`]/g, "'");
    var words = s.replace(/-/g, ' ').split(/[^a-z0-9']+/).filter(Boolean);
    var out = [];
    words.forEach(function (w) {
      w = w.replace(/^'+|'+$/g, '');
      if (!w) return;
      if (/^\d+$/.test(w)) {
        var n = parseInt(w, 10);
        w = n <= 20 ? NUMS[n] : (TENS[n] || w);
      }
      out.push(CONTR[w] || w);
    });
    out = out.join(' ').split(' ').map(function (w) { return HOMO[w] || w; });
    return out.join(' ');
  }

  function lev(a, b) {
    var m = a.length, n = b.length, i, j, prev = [], cur;
    for (j = 0; j <= n; j++) prev[j] = j;
    for (i = 1; i <= m; i++) {
      cur = [i];
      for (j = 1; j <= n; j++) {
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      }
      prev = cur;
    }
    return prev[n];
  }

  function sim1(a, b) {
    a = norm(a); b = norm(b);
    if (!a || !b) return 0;
    if (a === b) return 1;
    var best = 1 - lev(a, b) / Math.max(a.length, b.length);
    var aw = a.split(' '), bw = b.split(' ');
    // целевое слово есть среди сказанных («the cat» → cat): почти хорошо
    if (bw.length === 1 && aw.indexOf(b) !== -1) best = Math.max(best, 0.9);
    // фраза: доля совпавших слов
    if (bw.length > 1) {
      var left = aw.slice(), hit = 0;
      bw.forEach(function (w) { var i = left.indexOf(w); if (i !== -1) { hit++; left.splice(i, 1); } });
      best = Math.max(best, hit / Math.max(aw.length, bw.length) * (hit === bw.length && aw.length === bw.length ? 1 : 0.95));
    }
    var a2 = a.replace(/ /g, ''), b2 = b.replace(/ /g, '');
    if (a2 === b2) return 1;
    return Math.max(best, 1 - lev(a2, b2) / Math.max(a2.length, b2.length));
  }

  /* heard: [{text, confidence}], accepts: ['Mother','Mom'] → 0..1 */
  function similarity(heard, accepts) {
    var best = 0;
    (heard || []).forEach(function (h, i) {
      accepts.forEach(function (t) {
        var s = sim1(h.text, t);
        // не первая гипотеза или неуверенное распознавание — не больше «двух звёзд»
        if ((i > 0 || (typeof h.confidence === 'number' && h.confidence > 0 && h.confidence < 0.6)) && s > 0.9) s = 0.9;
        if (s > best) best = s;
      });
    });
    return best;
  }

  function stars(sim) { return sim >= 0.99 ? 3 : sim >= 0.8 ? 2 : sim >= 0.5 ? 1 : 0; }

  var ERRORS = {
    'not-allowed': 'Микрофон не разрешён 🔒 Нажми на замочек рядом с адресом сайта и разреши микрофон.',
    'service-not-allowed': 'Микрофон не разрешён 🔒 Разреши его в настройках браузера.',
    'no-speech': 'Я ничего не услышал 🙈 Нажми 🎤 и скажи погромче.',
    'audio-capture': 'Не нашёл микрофон 🎙️ Проверь, что он подключён.',
    'network': 'Нет связи с распознаванием речи 📡 Проверь интернет.',
    'aborted': '',
    'unsupported': 'Этот браузер не умеет слушать 🙁 Открой сайт в Chrome, Edge или Safari.'
  };

  var current = null;
  function stopCurrent() { if (current) { try { current.abort(); } catch (e) { /* noop */ } current = null; } }

  /* Слушаем один раз. cb(err, [{text, confidence}]) */
  function listen(cb, onStart) {
    if (!SR) { cb('unsupported'); return; }
    stopCurrent();
    try { if (root.speechSynthesis) root.speechSynthesis.cancel(); } catch (e) { /* noop */ }
    var rec = new SR(), done = false, got = null, timer;
    current = rec;
    rec.lang = 'en-US';
    rec.interimResults = true;      // ловим и промежуточный результат — короткие слова иногда не доходят до «финала»
    rec.continuous = false;
    rec.maxAlternatives = 5;
    function finish(err, res) {
      if (done) return;
      done = true; clearTimeout(timer);
      if (current === rec) current = null;
      cb(err, res);
    }
    rec.onstart = function () { if (onStart) onStart(); };
    rec.onresult = function (e) {
      var r = e.results[e.results.length - 1], list = [];
      for (var i = 0; i < r.length; i++) list.push({ text: r[i].transcript, confidence: r[i].confidence });
      got = list;
      if (r.isFinal) { try { rec.stop(); } catch (x) { /* noop */ } }
    };
    rec.onerror = function (e) { finish(e.error || 'error'); };
    rec.onend = function () { finish(got ? null : 'no-speech', got); };
    timer = setTimeout(function () { try { rec.stop(); } catch (e) { /* noop */ } }, 8000);
    try { rec.start(); } catch (e) { finish('error'); }
  }

  function csrf() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.content : '';
  }

  function save(target, score, lesson) {
    return fetch('/api/speak', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ target: target, score: score, lesson: lesson || 0 })
    }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function starsHtml(n) { return '⭐'.repeat(n) + '<span class="sp-off">' + '☆'.repeat(3 - n) + '</span>'; }

  /* Рисует список слов с кнопками 🔊 🐢 🎤 */
  function renderBlock(block, opts) {
    opts = opts || {};
    var items = [];
    try { items = JSON.parse(block.dataset.items || '[]'); } catch (e) { /* noop */ }
    var lessonDefault = parseInt(block.dataset.lesson || '0', 10) || 0;
    var results = {}, total = items.length;
    block.innerHTML = '';
    if (!SR) block.appendChild(el('p', 'sp-note', ERRORS.unsupported + ' Слова можно послушать кнопкой 🔊.'));
    else block.appendChild(el('p', 'sp-note', 'Нажми 🔊 — послушай, потом 🎤 и скажи слово вслух. Говори сразу, когда кнопка стала красной ⏺, — чётко и не слишком тихо.'));

    items.forEach(function (it, idx) {
      var row = el('div', 'sp-row');
      row.innerHTML = '<div class="sp-word"><b>' + esc(it.en) + '</b><span>' + esc(it.ru) + '</span></div>' +
        '<div class="sp-btns"><button type="button" class="btn btn-small sp-say" title="Послушать">🔊</button>' +
        '<button type="button" class="btn btn-small sp-slow" title="Медленно">🐢</button>' +
        (SR ? '<button type="button" class="btn btn-small btn-primary sp-mic" title="Сказать вслух">🎤</button>' : '') +
        '</div><div class="sp-res" aria-live="polite"></div>';
      var res = row.querySelector('.sp-res'), mic = row.querySelector('.sp-mic');
      row.querySelector('.sp-say').onclick = function () { if (root.ttsSpeak) root.ttsSpeak(it.en); };
      row.querySelector('.sp-slow').onclick = function () { if (root.ttsSpeak) root.ttsSpeak(it.en, 0.5); };
      if (mic) mic.onclick = function () {
        if (mic.classList.contains('listening')) { stopCurrent(); return; }
        block.querySelectorAll('.sp-mic.listening').forEach(function (b) { b.classList.remove('listening'); });
        res.className = 'sp-res'; res.textContent = '';
        listen(function (err, heard) {
          mic.classList.remove('listening'); mic.textContent = '🎤';
          if (err) {
            if (err !== 'aborted') {
              res.className = 'sp-res sp-err';
              res.textContent = ERRORS[err] !== undefined ? ERRORS[err] : 'Не получилось 😕 Попробуй ещё раз.';
              if (err === 'no-speech') document.dispatchEvent(new CustomEvent('speak:result', { detail: { stars: 0 } }));
            }
            return;
          }
          var sim = similarity(heard, it.accept || [it.en]), st = stars(sim);
          res.className = 'sp-res st' + st;
          res.innerHTML = '<span class="sp-stars">' + starsHtml(st) + '</span> <span class="sp-heard">я услышал: «' +
            esc(heard[0].text) + '»' + (st < 3 && heard.length > 1 ? ' (ещё: ' + esc(heard.slice(1, 4).map(function (h) { return h.text; }).join(', ')) + ')' : '') + '</span>';
          var prev = results[idx];
          results[idx] = Math.max(prev == null ? -1 : prev, st);
          document.dispatchEvent(new CustomEvent('speak:result', { detail: { stars: st, target: it.en } }));
          save(it.en, st, it.lesson || lessonDefault).then(function (j) {
            if (j && j.newAchievements && j.newAchievements.length) {
              setTimeout(function () {
                document.dispatchEvent(new CustomEvent('speak:achievements', { detail: { list: j.newAchievements } }));
              }, 1800);
            }
          });
          if (opts.onProgress) opts.onProgress(results, total);
        }, function () { mic.classList.add('listening'); mic.textContent = '⏺'; });
      };
      block.appendChild(row);
    });
    return { results: results };
  }

  root.Speak = { supported: !!SR, norm: norm, similarity: similarity, stars: stars, listen: listen, save: save, renderBlock: renderBlock };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.Speak;

  if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', function () {
    var b = document.getElementById('speak-block');
    if (b) renderBlock(b);
    var page = document.getElementById('speak-page');
    if (page) {
      var sum = document.getElementById('sp-summary');
      renderBlock(page, {
        onProgress: function (results, total) {
          var done = Object.keys(results).length;
          if (done < total || !sum) return;
          var sumStars = 0;
          Object.keys(results).forEach(function (k) { sumStars += results[k]; });
          sum.classList.remove('hidden');
          sum.querySelector('.sp-sum-num').textContent = sumStars + ' из ' + (total * 3);
        }
      });
    }
  });
})(typeof window !== 'undefined' ? window : globalThis);
