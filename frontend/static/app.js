/* ============================================================
   BISfit — app.js
   Handles API calls, loading states, result rendering
   ============================================================ */

const API_BASE = window.location.origin;           // same-origin via FastAPI
const FORM        = document.getElementById('query-form');
const INPUT       = document.getElementById('query-input');
const SUBMIT_BTN  = document.getElementById('submit-btn');
const LOADING     = document.getElementById('loading');
const LOADING_STEP= document.getElementById('loading-step');
const RESULT      = document.getElementById('result-panel');
const RESP_BODY   = document.getElementById('response-body');
const STD_CHIPS   = document.getElementById('standards-chips');
const STD_SECTION = document.getElementById('standards-section');
const LATENCY     = document.getElementById('latency-chip');
const ERROR_PANEL = document.getElementById('error-panel');
const ERROR_MSG   = document.getElementById('error-msg');
const STATUS_BADGE= document.getElementById('status-badge');

/* ---- Health check ---- */
async function checkHealth() {
  try {
    const r = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
    if (r.ok) {
      const d = await r.json();
      if (d.pipeline_ready) {
        STATUS_BADGE.textContent = '● Ready';
        STATUS_BADGE.classList.remove('error');
      } else {
        STATUS_BADGE.textContent = '● Pipeline loading…';
      }
    } else {
      throw new Error('non-ok');
    }
  } catch {
    STATUS_BADGE.textContent = '● Offline';
    STATUS_BADGE.classList.add('error');
  }
}
checkHealth();
setInterval(checkHealth, 30_000);

/* ---- Example pills ---- */
document.querySelectorAll('.pill').forEach(pill => {
  pill.addEventListener('click', () => {
    INPUT.value = pill.dataset.q;
    INPUT.focus();
  });
});

/* ---- Loading step messages (simulate progress UX) ---- */
const STEPS = [
  'Reformulating query with Llama 3 8b…',
  'Searching FAISS index across 584 chunks…',
  'Re-ranking by cosine similarity…',
  'Generating answer with Llama 3 70b…',
];
let stepInterval = null;
function startLoadingSteps() {
  let i = 0;
  LOADING_STEP.textContent = STEPS[0];
  stepInterval = setInterval(() => {
    i = (i + 1) % STEPS.length;
    LOADING_STEP.textContent = STEPS[i];
  }, 2200);
}
function stopLoadingSteps() {
  clearInterval(stepInterval);
  stepInterval = null;
}

/* ---- UI state helpers ---- */
function showLoading() {
  LOADING.classList.remove('hidden');
  RESULT.classList.add('hidden');
  ERROR_PANEL.classList.add('hidden');
  SUBMIT_BTN.disabled = true;
  startLoadingSteps();
}
function hideLoading() {
  LOADING.classList.add('hidden');
  SUBMIT_BTN.disabled = false;
  stopLoadingSteps();
}
function showResult(data) {
  RESP_BODY.textContent = data.response;
  LATENCY.textContent   = `⚡ ${data.latency_seconds.toFixed(2)}s`;

  STD_CHIPS.innerHTML = '';
  if (data.retrieved_standards && data.retrieved_standards.length > 0) {
    STD_SECTION.classList.remove('hidden');
    data.retrieved_standards.forEach(std => {
      const chip = document.createElement('span');
      chip.className = 'std-chip';
      chip.textContent = std;
      STD_CHIPS.appendChild(chip);
    });
  } else {
    STD_SECTION.classList.add('hidden');
  }

  RESULT.classList.remove('hidden');
}
function showError(msg) {
  ERROR_MSG.textContent = msg;
  ERROR_PANEL.classList.remove('hidden');
}

/* ---- Form submit ---- */
FORM.addEventListener('submit', async (e) => {
  e.preventDefault();
  const query = INPUT.value.trim();
  if (!query) return;

  showLoading();

  try {
    const res = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });

    hideLoading();

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      showError(`Server error ${res.status}: ${err.detail || 'Unknown error'}`);
      return;
    }

    const data = await res.json();
    showResult(data);

  } catch (err) {
    hideLoading();
    showError(`Could not reach the BISfit API. Make sure the server is running at ${API_BASE}. (${err.message})`);
  }
});

/* ---- Allow Shift+Enter for newlines, Enter to submit ---- */
INPUT.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    FORM.dispatchEvent(new Event('submit'));
  }
});
