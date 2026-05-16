/* DS単語 — Core application logic */

(function () {
  'use strict';

  // ============ Constants ============
  const STORAGE_KEY = 'ds-tango-state-v1';
  const STORAGE_VERSION = 1;
  const DATA_URL = 'data/vocabulary.json';
  const I18N_URL = 'i18n/ja.json';
  const FEEDBACK_URL = ''; // TODO: paste your Google Form URL here when ready

  const TRANSLATION_LANGS = ['en', 'zh', 'my', 'mn', 'id', 'ne'];
  const DEFAULT_LANG = 'en';
  const VERIFIED_LANGS = ['zh', 'en']; // others show ⚠ badge

  // ============ State ============
  /** @type {{version:number, translation_lang:string, progress:Object<string,string>, last_seen:Object<string,string>, first_open:boolean, lang_chosen:boolean, onb_done:boolean}} */
  let state = null;
  /** @type {{words:Array, _meta:Object}|null} */
  let vocab = null;
  /** @type {Object|null} */
  let i18n = null;
  /** @type {Object|null} */
  let currentWord = null;
  let isExpanded = false;
  let currentView = null;
  let modalContext = null;

  // ============ DOM helpers ============
  const $ = (id) => document.getElementById(id);
  const $$ = (sel) => document.querySelectorAll(sel);

  function format(tmpl, vars) {
    return tmpl.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`));
  }

  // ============ Storage ============
  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultState();
      const parsed = JSON.parse(raw);
      if (parsed.version !== STORAGE_VERSION) return defaultState();
      return Object.assign(defaultState(), parsed);
    } catch (e) {
      console.warn('Failed to load state, resetting:', e);
      return defaultState();
    }
  }
  function defaultState() {
    return {
      version: STORAGE_VERSION,
      translation_lang: DEFAULT_LANG,
      progress: {}, // id -> 'new' | 'learning' | 'mastered' (only learning/mastered actually stored; new is implicit)
      last_seen: {}, // id -> ISO timestamp
      first_open: true,
      lang_chosen: false,
      onb_done: false,
    };
  }
  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.warn('Failed to save state:', e);
    }
  }

  // ============ Vocabulary & i18n loading ============
  async function loadVocab() {
    const resp = await fetch(DATA_URL, { cache: 'force-cache' });
    if (!resp.ok) throw new Error('Failed to load vocabulary.json');
    return resp.json();
  }
  async function loadI18n() {
    const resp = await fetch(I18N_URL, { cache: 'force-cache' });
    if (!resp.ok) throw new Error('Failed to load i18n/ja.json');
    return resp.json();
  }

  // ============ Progress helpers ============
  function statusOf(id) {
    return state.progress[id] || 'new';
  }
  function setStatus(id, status) {
    if (status === 'new') {
      delete state.progress[id];
    } else {
      state.progress[id] = status;
    }
    saveState();
  }
  function touchSeen(id) {
    state.last_seen[id] = new Date().toISOString();
    saveState();
  }
  function countByStatus() {
    const total = vocab.words.length;
    let mastered = 0, learning = 0;
    for (const w of vocab.words) {
      const s = statusOf(w.id);
      if (s === 'mastered') mastered++;
      else if (s === 'learning') learning++;
    }
    return { total, mastered, learning, remaining: total - mastered };
  }

  // ============ Queue logic (PRD §3.2) ============
  // Target size of the "learning" queue before we start recycling old words.
  // Until the queue has this many words, "次へ" prefers fresh words; afterwards
  // it cycles oldest-first through the learning queue.
  const LEARNING_QUEUE_TARGET = 7;

  /**
   * Pick the next word to show.
   * Strategy:
   *   1. Never return the current word if any alternative exists.
   *   2. While the learning queue is small (< LEARNING_QUEUE_TARGET), grow it with fresh words.
   *   3. Once large enough, cycle through learning words oldest-first.
   *   4. If only the current word remains unmastered, return it (user must decide).
   *   5. If everything is mastered, return null → done page.
   */
  function pickNextWord() {
    const currentId = currentWord ? currentWord.id : null;
    const learning = [];
    const fresh = [];
    for (const w of vocab.words) {
      const s = statusOf(w.id);
      if (s === 'mastered') continue;
      if (s === 'learning') learning.push(w);
      else fresh.push(w);
    }

    if (learning.length === 0 && fresh.length === 0) return null;

    const learningOthers = currentId ? learning.filter((w) => w.id !== currentId) : learning;
    const freshOthers = currentId ? fresh.filter((w) => w.id !== currentId) : fresh;

    // If only the current word remains unmastered, return it
    if (learningOthers.length === 0 && freshOthers.length === 0) {
      return currentWord;
    }

    // Sort learning by last_seen ascending (oldest first)
    learningOthers.sort((a, b) => {
      const la = state.last_seen[a.id] || '';
      const lb = state.last_seen[b.id] || '';
      return la < lb ? -1 : la > lb ? 1 : 0;
    });

    // Grow the learning queue with fresh words until it reaches the target
    if (learning.length < LEARNING_QUEUE_TARGET && freshOthers.length > 0) {
      return freshOthers[0];
    }

    // Queue is full enough — cycle oldest learning, fall back to fresh if none
    if (learningOthers.length === 0) return freshOthers[0];
    return learningOthers[0];
  }

  // ============ View routing ============
  function showView(name) {
    currentView = name;
    $$('.view').forEach((v) => {
      v.hidden = v.id !== `view-${name}`;
    });
    window.scrollTo(0, 0);
  }

  // ============ Audio ============
  let currentAudioBtn = null;
  function playAudio(path, btn) {
    const audio = $('audio');
    // Stop any previous
    audio.pause();
    audio.currentTime = 0;
    if (currentAudioBtn) currentAudioBtn.classList.remove('playing');
    currentAudioBtn = btn || null;
    if (currentAudioBtn) currentAudioBtn.classList.add('playing');
    audio.src = path;
    const stop = () => {
      if (currentAudioBtn) {
        currentAudioBtn.classList.remove('playing');
        currentAudioBtn = null;
      }
    };
    audio.onended = stop;
    audio.onerror = () => {
      stop();
      // Silently fail — audio may not be generated yet (PRD: generate after vocab finalized)
      console.warn('Audio not available:', path);
      toast('音声ファイルが見つかりません');
    };
    const p = audio.play();
    if (p && typeof p.catch === 'function') p.catch(stop);
  }

  // ============ Toast ============
  let toastTimer = null;
  function toast(msg, ms = 1800) {
    const el = $('toast');
    el.textContent = msg;
    el.hidden = false;
    requestAnimationFrame(() => el.classList.add('show'));
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.classList.remove('show');
      setTimeout(() => { el.hidden = true; }, 250);
    }, ms);
  }

  // ============ Card rendering ============
  function showNextCard() {
    const w = pickNextWord();
    if (!w) {
      showView('done');
      // refresh done text with total
      const doneSub = $('view-done').querySelector('p');
      doneSub.innerHTML = format(i18n.ui.doneSubFormat, { n: vocab.words.length })
        .replace(/\n/g, '<br>');
      return;
    }
    currentWord = w;
    isExpanded = false;
    renderCard(w);
    // First-time exposure transitions to learning (PRD §3.2)
    if (statusOf(w.id) === 'new') {
      setStatus(w.id, 'learning');
    }
    touchSeen(w.id);
    updateProgressDisplay();
    showView('card');
  }

  function renderCard(w) {
    // Word
    const wordEl = $('card-word');
    wordEl.textContent = w.jp.word;
    wordEl.classList.remove('smaller', 'compound-2line');
    if (isExpanded) {
      wordEl.classList.add('smaller');
    } else if (w.jp.word.length >= 8) {
      wordEl.classList.add('compound-2line');
    }

    // Reading (only when expanded)
    const readingEl = $('card-reading');
    readingEl.textContent = w.jp.reading;
    readingEl.hidden = !isExpanded;

    // Word block padding
    $('word-block').classList.toggle('expanded', isExpanded);

    // Info wrap
    $('info-wrap').hidden = !isExpanded;

    if (isExpanded) {
      $('card-jp-def').textContent = w.jp.definition;
      $('card-jp-ex').textContent = w.jp.example;

      const lang = state.translation_lang;
      const tr = w.translations[lang] || {};
      const labels = i18n.labels[lang] || { definition: 'Definition', example: 'Example' };

      const trDef = $('card-tr-def');
      const trEx = $('card-tr-ex');
      const trBlock = $('tr-block');
      if (tr.definition) {
        trBlock.hidden = false;
        $('tr-label-def').textContent = labels.definition;
        $('tr-label-ex').textContent = labels.example;
        trDef.textContent = tr.definition;
        trDef.setAttribute('lang', lang);
        trEx.textContent = tr.example || '';
        trEx.setAttribute('lang', lang);
      } else {
        trBlock.hidden = true;
      }

      // Verify badge for unverified languages
      const verifiedKey = `verified_${lang}`;
      const verified = w.review_status && w.review_status[verifiedKey];
      $('tr-verify-badge').hidden = verified || VERIFIED_LANGS.includes(lang);
    }

    // Bottom button text
    $('card-bottom-btn').textContent = isExpanded ? i18n.ui.cardNextBtn : i18n.ui.cardMeaningBtn;
    $('card-bottom-btn').classList.toggle('primary', isExpanded);
  }

  function expandCard() {
    isExpanded = true;
    renderCard(currentWord);
    // Scroll card-area to top so user sees the word and the start of definitions
    $('card-area').scrollTop = 0;
    // Auto-play the word's pronunciation when meaning is revealed
    // (user-gesture-initiated, so iOS Safari allows it)
    if (currentWord && currentWord.audio && currentWord.audio.word) {
      const wordBtn = document.querySelector('.word-toolbar [data-action="play-word"]');
      playAudio(currentWord.audio.word, wordBtn);
    }
  }

  function updateProgressDisplay() {
    const c = countByStatus();
    const pct = c.total === 0 ? 0 : Math.round((c.mastered / c.total) * 100);
    $('progress-fill').style.width = pct + '%';
    $('progress-remaining').textContent = format(i18n.ui.progressRemainingFormat, { n: c.remaining });
    $('progress-mastered').textContent = format(i18n.ui.progressMasteredFormat, { m: c.mastered, t: c.total });
  }

  // ============ Mastered list view ============
  function renderMasteredList() {
    const list = $('mastered-list');
    list.innerHTML = '';
    const lang = state.translation_lang;
    const items = vocab.words.filter((w) => statusOf(w.id) === 'mastered');
    $('mastered-count').textContent = format(i18n.ui.masteredCountFormat, {
      m: items.length, t: vocab.words.length,
    });
    if (items.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'mastered-empty';
      empty.textContent = i18n.ui.masteredEmpty;
      list.appendChild(empty);
      return;
    }
    for (const w of items) {
      const tr = w.translations[lang] || {};
      const row = document.createElement('div');
      row.className = 'mastered-row';
      const left = document.createElement('div');
      const jp = document.createElement('div');
      jp.className = 'word-jp';
      jp.textContent = w.jp.word;
      const trw = document.createElement('div');
      trw.className = 'word-tr';
      trw.textContent = tr.word || '';
      trw.setAttribute('lang', lang);
      left.appendChild(jp);
      left.appendChild(trw);
      const btn = document.createElement('button');
      btn.className = 'restore';
      btn.textContent = i18n.ui.masteredRestore;
      btn.addEventListener('click', () => {
        setStatus(w.id, 'new');
        delete state.last_seen[w.id];
        saveState();
        renderMasteredList();
        updateProgressDisplay();
        toast('学習キューに戻しました');
      });
      row.appendChild(left);
      row.appendChild(btn);
      list.appendChild(row);
    }
  }

  // ============ Settings view ============
  function renderSettings() {
    const lang = state.translation_lang;
    $('setting-lang-value').textContent = i18n.languages[lang]?.displayName || lang;
    const c = countByStatus();
    $('setting-mastered-value').textContent = format(i18n.ui.masteredCountFormat, { m: c.mastered, t: c.total });
    const dataDate = vocab._meta?.generated_date || '—';
    $('settings-meta').innerHTML = format(i18n.ui.settingsMetaFormat, {
      version: i18n.ui.version, date: dataDate,
    }).replace(/\n/g, '<br>');
  }

  // ============ Language select view ============
  function renderLangList(includeJa = false) {
    const list = $('lang-list');
    list.innerHTML = '';
    for (const code of TRANSLATION_LANGS) {
      const meta = i18n.languages[code];
      if (!meta) continue;
      const item = document.createElement('div');
      item.className = 'lang-item';
      if (code === state.translation_lang) item.classList.add('active');
      item.setAttribute('data-lang', code);
      const name = document.createElement('span');
      name.className = 'lang-name';
      name.textContent = meta.displayName;
      name.setAttribute('lang', code);
      const right = document.createElement('span');
      if (code === state.translation_lang) {
        right.className = 'checkmark';
        right.textContent = '✓';
      } else {
        right.className = 'lang-en';
        right.textContent = meta.subName;
      }
      item.appendChild(name);
      item.appendChild(right);
      item.addEventListener('click', () => {
        state.translation_lang = code;
        saveState();
        renderLangList();
      });
      list.appendChild(item);
    }
  }

  // ============ Onboarding ============
  let onbStep = 1;
  function renderOnboarding() {
    onbStep = 1;
    showOnbStep(1);
  }
  function showOnbStep(n) {
    onbStep = n;
    $$('.onb-slide').forEach((el) => {
      el.hidden = parseInt(el.dataset.step, 10) !== n;
    });
    $$('.dot').forEach((el, i) => {
      el.classList.toggle('active', i + 1 === n);
    });
    $('onb-next-btn').textContent = n === 3 ? i18n.ui.onbStart : i18n.ui.onbNext;
  }

  // ============ Modal ============
  function openModal({ title, bodyHTML, footerHTML, ctx }) {
    $('modal-title').textContent = title;
    $('modal-body').innerHTML = bodyHTML;
    $('modal-footer').innerHTML = footerHTML || `<button class="btn-action" data-action="close-modal">${i18n.ui.modalClose}</button>`;
    modalContext = ctx || null;
    $('modal').hidden = false;
  }
  function closeModal() {
    $('modal').hidden = true;
    modalContext = null;
  }

  function openExportModal() {
    const payload = JSON.stringify(state, null, 2);
    const body = `
      <p>${i18n.ui.modalExportHint}</p>
      <textarea id="export-text" readonly>${escapeHtml(payload)}</textarea>
    `;
    const footer = `
      <button class="btn-action" data-action="export-copy">${i18n.ui.modalExportCopy}</button>
      <button class="btn-action" data-action="close-modal">${i18n.ui.modalClose}</button>
    `;
    openModal({ title: i18n.ui.modalExportTitle, bodyHTML: body, footerHTML: footer });
  }
  function openImportModal() {
    const body = `
      <p>${i18n.ui.modalImportHint}</p>
      <textarea id="import-text" placeholder='{"version":1,...}'></textarea>
    `;
    const footer = `
      <button class="btn-action" data-action="close-modal">${i18n.ui.modalCancel}</button>
      <button class="btn-action primary" data-action="import-confirm">${i18n.ui.modalImportBtn}</button>
    `;
    openModal({ title: i18n.ui.modalImportTitle, bodyHTML: body, footerHTML: footer });
  }
  function openAboutModal() {
    const body = `<p>${escapeHtml(i18n.ui.modalAboutBody).replace(/\n/g, '<br>')}</p>`;
    openModal({ title: i18n.ui.modalAboutTitle, bodyHTML: body });
  }
  function openFeedbackModal() {
    let body;
    if (FEEDBACK_URL) {
      body = `<p>${escapeHtml(i18n.ui.modalFeedbackBody).replace(/\n.*$/m, '')}</p><p><a href="${FEEDBACK_URL}" target="_blank" rel="noopener">${FEEDBACK_URL}</a></p>`;
    } else {
      body = `<p>${escapeHtml(i18n.ui.modalFeedbackBody).replace(/\n/g, '<br>')}</p>`;
    }
    openModal({ title: i18n.ui.modalFeedbackTitle, bodyHTML: body });
  }
  function openResetModal() {
    const body = `<p>${escapeHtml(i18n.ui.modalResetBody)}</p>`;
    const footer = `
      <button class="btn-action" data-action="close-modal">${i18n.ui.modalCancel}</button>
      <button class="btn-action primary" data-action="reset-confirm" style="background:var(--danger);border-color:var(--danger)">${i18n.ui.modalResetConfirm}</button>
    `;
    openModal({ title: i18n.ui.modalResetTitle, bodyHTML: body, footerHTML: footer });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // ============ Action handlers ============
  const actions = {
    'welcome-start': () => {
      state.first_open = false;
      saveState();
      renderLangList();
      showView('lang-select');
    },
    'lang-confirm': () => {
      state.lang_chosen = true;
      saveState();
      if (!state.onb_done) {
        renderOnboarding();
        showView('onboarding');
      } else {
        showNextCard();
      }
    },
    'onb-next': () => {
      if (onbStep < 3) {
        showOnbStep(onbStep + 1);
      } else {
        state.onb_done = true;
        saveState();
        showNextCard();
      }
    },
    'card-bottom': () => {
      if (!isExpanded) {
        expandCard();
      } else {
        showNextCard();
      }
    },
    'mark-mastered': () => {
      if (!currentWord) return;
      setStatus(currentWord.id, 'mastered');
      toast('「覚えた」に追加しました');
      showNextCard();
    },
    'play-word': (btn) => {
      if (!currentWord) return;
      playAudio(currentWord.audio.word, btn);
    },
    'play-def': (btn) => {
      if (!currentWord) return;
      playAudio(currentWord.audio.definition, btn);
    },
    'play-ex': (btn) => {
      if (!currentWord) return;
      playAudio(currentWord.audio.example, btn);
    },
    'open-mastered': () => {
      renderMasteredList();
      showView('mastered');
    },
    'open-settings': () => {
      renderSettings();
      showView('settings');
    },
    'back-to-card': () => {
      if (!currentWord) {
        showNextCard();
      } else {
        showView('card');
      }
    },
    'change-lang': () => {
      renderLangList();
      // Re-purpose lang-select view but keep confirm button -> go back to settings
      const confirmBtn = $('lang-confirm-btn');
      confirmBtn.textContent = i18n.ui.modalOk;
      confirmBtn.onclick = () => {
        confirmBtn.onclick = null;
        confirmBtn.textContent = i18n.ui.langConfirm;
        renderSettings();
        showView('settings');
      };
      showView('lang-select');
    },
    'export-progress': openExportModal,
    'import-progress': openImportModal,
    'export-copy': () => {
      const ta = $('export-text');
      ta.select();
      try {
        navigator.clipboard.writeText(ta.value).then(() => {
          toast(i18n.ui.modalExportCopied);
        });
      } catch (e) {
        document.execCommand('copy');
        toast(i18n.ui.modalExportCopied);
      }
    },
    'import-confirm': () => {
      const ta = $('import-text');
      try {
        const parsed = JSON.parse(ta.value.trim());
        if (typeof parsed !== 'object' || parsed.version !== STORAGE_VERSION) {
          throw new Error('invalid');
        }
        state = Object.assign(defaultState(), parsed);
        saveState();
        closeModal();
        toast(i18n.ui.modalImportSuccess);
        renderSettings();
      } catch (e) {
        toast(i18n.ui.modalImportInvalid);
      }
    },
    'feedback': openFeedbackModal,
    'about': openAboutModal,
    'reset-all': openResetModal,
    'reset-confirm': () => {
      state = defaultState();
      saveState();
      closeModal();
      currentWord = null;
      isExpanded = false;
      toast('リセットしました');
      // Restart from welcome flow
      bootApp();
    },
    'close-modal': closeModal,
  };

  // ============ Event binding ============
  function bindGlobalEvents() {
    document.body.addEventListener('click', (e) => {
      const target = e.target.closest('[data-action]');
      if (!target) return;
      const action = target.dataset.action;
      const fn = actions[action];
      if (fn) {
        e.preventDefault();
        fn(target);
      }
    });
    // Lang item clicks (lang-select)
    $('lang-list').addEventListener('click', (e) => {
      const item = e.target.closest('.lang-item');
      if (!item) return;
      const code = item.dataset.lang;
      if (code) {
        state.translation_lang = code;
        saveState();
        renderLangList();
      }
    });
  }

  // ============ Boot ============
  async function bootApp() {
    // First-open routing
    if (state.first_open) {
      showView('welcome');
      return;
    }
    if (!state.lang_chosen) {
      renderLangList();
      showView('lang-select');
      return;
    }
    if (!state.onb_done) {
      renderOnboarding();
      showView('onboarding');
      return;
    }
    showNextCard();
  }

  async function main() {
    state = loadState();
    try {
      [vocab, i18n] = await Promise.all([loadVocab(), loadI18n()]);
    } catch (e) {
      document.body.innerHTML = `<div style="padding:48px;font-family:sans-serif">読み込みエラー: ${escapeHtml(e.message)}</div>`;
      return;
    }
    bindGlobalEvents();
    bootApp();

    // Register service worker (PWA offline support)
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('service-worker.js').catch((err) => {
        console.warn('SW registration failed:', err);
      });
    }
  }

  document.addEventListener('DOMContentLoaded', main);
})();
