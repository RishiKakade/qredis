(() => {
  const keysEl = document.getElementById('keys');
  const patternEl = document.getElementById('pattern');
  const loadBtn = document.getElementById('load');
  const cursorEl = document.getElementById('cursor');
  const prevBtn = document.getElementById('prev');
  const nextBtn = document.getElementById('next');

  const metaKey = document.getElementById('meta-key');
  const metaType = document.getElementById('meta-type');
  const metaTTL = document.getElementById('meta-ttl');
  const valueEl = document.getElementById('value');
  const saveBtn = document.getElementById('save');
  const deleteBtn = document.getElementById('delete');

  let currentCursor = 0;
  let lastPattern = '*';
  let currentKey = null;
  let currentType = null;

  async function fetchJSON(url, opts) {
    const res = await fetch(url, opts);
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`HTTP ${res.status}: ${txt}`);
    }
    return res.json();
  }

  function setPager(cursor, enableNext) {
    currentCursor = cursor;
    cursorEl.textContent = String(cursor);
    prevBtn.disabled = cursor === 0;
    nextBtn.disabled = !enableNext && cursor === 0;
    nextBtn.disabled = cursor === 0 ? nextBtn.disabled : false;
  }

  async function loadKeys(cursor=0) {
    const pattern = patternEl.value || '*';
    lastPattern = pattern;
    const data = await fetchJSON(`/api/keys?pattern=${encodeURIComponent(pattern)}&cursor=${cursor}&count=100`);
    keysEl.innerHTML = '';
    for (const k of data.keys) {
      const li = document.createElement('li');
      li.textContent = k;
      li.title = k;
      li.addEventListener('click', () => openKey(k));
      keysEl.appendChild(li);
    }
    setPager(data.cursor, data.keys.length > 0 && data.cursor !== 0);
  }

  async function openKey(key) {
    const data = await fetchJSON(`/api/key/${encodeURIComponent(key)}`);
    currentKey = data.key;
    currentType = data.type;
    metaKey.textContent = data.key;
    metaType.textContent = data.type;
    metaTTL.value = data.ttl;
    valueEl.innerHTML = '';
    saveBtn.disabled = true;
    deleteBtn.disabled = false;

    if (data.type === 'string') {
      const ta = document.createElement('textarea');
      ta.value = data.value ?? '';
      ta.rows = 16; ta.cols = 80;
      ta.addEventListener('input', () => { saveBtn.disabled = false; });
      valueEl.appendChild(ta);
      saveBtn.disabled = false;
    } else {
      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify(data.value, null, 2);
      valueEl.appendChild(pre);
      saveBtn.disabled = true;
    }
  }

  async function save() {
    if (!currentKey) return;
    if (currentType !== 'string') return;
    const ta = valueEl.querySelector('textarea');
    const ttl = parseInt(metaTTL.value, 10);
    const body = { type: 'string', value: ta.value, ttl: isNaN(ttl) ? -1 : ttl };
    await fetchJSON(`/api/key/${encodeURIComponent(currentKey)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    saveBtn.disabled = true;
  }

  async function del() {
    if (!currentKey) return;
    if (!confirm(`Delete key "${currentKey}"?`)) return;
    await fetchJSON(`/api/key/${encodeURIComponent(currentKey)}`, { method: 'DELETE' });
    currentKey = null;
    metaKey.textContent = '';
    metaType.textContent = '';
    metaTTL.value = -1;
    valueEl.innerHTML = '';
    deleteBtn.disabled = true;
    saveBtn.disabled = true;
    loadKeys(currentCursor);
  }

  loadBtn.addEventListener('click', () => loadKeys(0));
  nextBtn.addEventListener('click', () => loadKeys(currentCursor));
  prevBtn.addEventListener('click', () => loadKeys(0));
  saveBtn.addEventListener('click', save);
  deleteBtn.addEventListener('click', del);

  // Auto-load
  loadKeys(0);
})();

