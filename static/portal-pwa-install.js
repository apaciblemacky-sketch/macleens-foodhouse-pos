(function () {
  'use strict';

  var script = document.currentScript;
  if (!script) return;
  var appName = script.dataset.pwaName || 'Macleen App';
  var swUrl = script.dataset.pwaSw || '';
  var scope = script.dataset.pwaScope || '/';
  var appKey = script.dataset.pwaKey || appName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  var autoPrompt = script.dataset.pwaAutoprompt === '1';
  var deferredPrompt = null;
  var promptCard = null;
  var DISMISS_MS = 7 * 24 * 60 * 60 * 1000;

  function isStandalone() {
    return (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) || window.navigator.standalone === true;
  }
  function isMobile() {
    return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || '') || Math.min(screen.width || 9999, screen.height || 9999) < 900;
  }
  function dismissalKey() { return 'mfh-pwa-install-dismissed:' + appKey; }
  function wasRecentlyDismissed() {
    try { return Date.now() - Number(localStorage.getItem(dismissalKey()) || 0) < DISMISS_MS; } catch (_) { return false; }
  }
  function rememberDismissal() { try { localStorage.setItem(dismissalKey(), String(Date.now())); } catch (_) {} }

  function setMode() {
    var standalone = isStandalone();
    document.documentElement.dataset.portalStandalone = standalone ? '1' : '0';
    document.querySelectorAll('[data-portal-install]').forEach(function (btn) { if (standalone) btn.style.display = 'none'; });
    if (standalone) removePromptCard();
  }

  function fallbackInstructions() {
    var ua = navigator.userAgent || '';
    if (/iPhone|iPad|iPod/i.test(ua)) { alert('Install ' + appName + ': tap Share in Safari, then choose “Add to Home Screen”.'); return; }
    if (/SamsungBrowser/i.test(ua)) { alert('Install ' + appName + ': open the browser menu (☰ or ⋮), then tap “Add page to” or “Install app”.'); return; }
    alert('Install ' + appName + ': open your browser menu (⋮) and choose “Install app” or “Add to Home screen”.');
  }

  async function installNow() {
    if (isStandalone()) return;
    if (!deferredPrompt) { fallbackInstructions(); return; }
    try {
      deferredPrompt.prompt();
      await deferredPrompt.userChoice;
    } catch (_) { fallbackInstructions(); }
    finally { deferredPrompt = null; removePromptCard(); }
  }

  function removePromptCard() { if (promptCard && promptCard.parentNode) promptCard.parentNode.removeChild(promptCard); promptCard = null; }
  function showPromptCard() {
    if (!autoPrompt || !isMobile() || isStandalone() || wasRecentlyDismissed() || promptCard) return;
    promptCard = document.createElement('div');
    promptCard.setAttribute('role', 'dialog');
    promptCard.setAttribute('aria-label', 'Install app');
    promptCard.innerHTML = '<div class="mfh-install-pop-icon">📲</div><div class="mfh-install-pop-copy"><strong>Install ' + escapeHtml(appName) + ' on your phone?</strong><span>Open it faster from your Home screen like an app.</span></div><div class="mfh-install-pop-actions"><button type="button" class="mfh-install-yes">Install</button><button type="button" class="mfh-install-no">Not now</button></div>';
    Object.assign(promptCard.style,{position:'fixed',left:'12px',right:'12px',bottom:'76px',zIndex:'10000',maxWidth:'560px',margin:'0 auto',background:'#fff',border:'1px solid #dbe7e4',borderRadius:'18px',boxShadow:'0 18px 50px rgba(15,23,42,.24)',padding:'13px',display:'grid',gridTemplateColumns:'40px 1fr',gap:'10px',alignItems:'center',fontFamily:'system-ui,-apple-system,Segoe UI,sans-serif'});
    var style=document.createElement('style'); style.textContent='.mfh-install-pop-copy strong{display:block;color:#172033;font-size:.92rem}.mfh-install-pop-copy span{display:block;color:#64748b;font-size:.75rem;margin-top:2px}.mfh-install-pop-actions{grid-column:2;display:flex;gap:8px}.mfh-install-pop-actions button{border:0;border-radius:10px;padding:8px 13px;font-weight:800;cursor:pointer}.mfh-install-yes{background:#0f766e;color:#fff}.mfh-install-no{background:#f1f5f9;color:#475569}.mfh-install-pop-icon{font-size:1.7rem;text-align:center}'; document.head.appendChild(style);
    promptCard.querySelector('.mfh-install-yes').addEventListener('click', installNow);
    promptCard.querySelector('.mfh-install-no').addEventListener('click', function(){ rememberDismissal(); removePromptCard(); });
    document.body.appendChild(promptCard);
  }
  function escapeHtml(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault(); deferredPrompt = event;
    document.querySelectorAll('[data-portal-install]').forEach(function (btn) { if (!isStandalone()) btn.hidden = false; });
    setTimeout(showPromptCard, 900);
  });
  window.addEventListener('appinstalled', function () { deferredPrompt = null; removePromptCard(); setMode(); });
  document.addEventListener('click', function (event) { var btn = event.target.closest('[data-portal-install]'); if (!btn) return; event.preventDefault(); installNow(); });

  if ('serviceWorker' in navigator && swUrl) {
    window.addEventListener('load', function () { navigator.serviceWorker.register(swUrl, { scope: scope }).catch(function (err) { console.warn('Portal PWA service worker registration failed:', err); }); });
  }
  window.addEventListener('load', function(){ if (autoPrompt) setTimeout(showPromptCard, 1600); });
  setMode();
  if (window.matchMedia) { var mq = window.matchMedia('(display-mode: standalone)'); if (mq.addEventListener) mq.addEventListener('change', setMode); }
})();
