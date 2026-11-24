// Eclipse Shield side panel: the primary, always-visible UI.
// It stays open across tab switches, shows backend health, the active
// profile, and the verdict for the current tab from /api/check.
// All state lives in chrome.storage; nothing is kept in page globals
// beyond this panel's own lifetime.
const API_BASE = 'http://127.0.0.1:5000';
let currentProfile = 'work';
let currentTabUrl = '';

async function refreshHealth() {
  const dot = document.getElementById('healthDot');
  const text = document.getElementById('healthText');
  const mode = document.getElementById('healthMode');
  try {
    const resp = await fetch(`${API_BASE}/health`);
    const data = await resp.json();
    dot.classList.add('on');
    text.textContent = 'Backend: online';
    mode.textContent = data.ai === 'configured'
      ? 'Mode: Gemini AI for unlisted sites'
      : 'Mode: local rules only (no Gemini key)';
  } catch (e) {
    dot.classList.remove('on');
    text.textContent = 'Backend: offline';
    mode.textContent = 'Start it with: python app.py';
  }
}

function renderProfiles() {
  document.querySelectorAll('#profiles button').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.profile === currentProfile);
  });
}

async function setProfile(profile) {
  currentProfile = profile;
  renderProfiles();
  await chrome.storage.local.set({ eclipseProfile: profile });
  // Keep an active session's domain in step with the panel switcher.
  const data = await chrome.storage.local.get(['sessionData']);
  if (data.sessionData && data.sessionData.state === 'active') {
    data.sessionData.domain = profile;
    await chrome.storage.local.set({ sessionData: data.sessionData });
  }
  if (currentTabUrl) checkCurrentTab();
}

async function refreshCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTabUrl = tab && tab.url ? tab.url : '';
  document.getElementById('url').textContent = currentTabUrl || 'No web page in this tab.';
  document.getElementById('checkBtn').disabled = !/^https?:/.test(currentTabUrl);
}

async function checkCurrentTab() {
  const box = document.getElementById('verdict');
  const state = document.getElementById('verdictState');
  const source = document.getElementById('verdictSource');
  const reason = document.getElementById('verdictReason');
  box.className = '';
  state.textContent = 'Checking...';
  source.textContent = '';
  reason.textContent = '';
  try {
    const data = await chrome.storage.local.get(['sessionData']);
    const context = (data.sessionData && data.sessionData.context) || [];
    const resp = await fetch(`${API_BASE}/api/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: currentTabUrl, profile: currentProfile, context }),
    });
    const verdict = await resp.json();
    if (!resp.ok) {
      state.textContent = 'Not checked';
      reason.textContent = verdict.error || `Backend returned ${resp.status}`;
      box.classList.add('show');
      return;
    }
    box.classList.add('show', verdict.allowed ? 'allow' : 'block');
    state.textContent = verdict.allowed ? 'Allowed' : 'Blocked';
    source.textContent = `source: ${verdict.source}`;
    reason.textContent = verdict.reason;
  } catch (e) {
    box.classList.add('show', 'block');
    state.textContent = 'Backend offline';
    source.textContent = '';
    reason.textContent = 'Start the local backend with: python app.py';
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const stored = await chrome.storage.local.get(['eclipseProfile', 'sessionData']);
  currentProfile = stored.eclipseProfile
    || (stored.sessionData && stored.sessionData.domain)
    || 'work';
  renderProfiles();
  document.querySelectorAll('#profiles button').forEach((btn) => {
    btn.addEventListener('click', () => setProfile(btn.dataset.profile));
  });
  document.getElementById('checkBtn').addEventListener('click', checkCurrentTab);
  await refreshHealth();
  await refreshCurrentTab();
  if (currentTabUrl) checkCurrentTab();
});

chrome.tabs.onActivated.addListener(async () => {
  await refreshCurrentTab();
  if (currentTabUrl) checkCurrentTab();
});
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo) => {
  if (changeInfo.url) {
    await refreshCurrentTab();
    if (currentTabUrl) checkCurrentTab();
  }
});
