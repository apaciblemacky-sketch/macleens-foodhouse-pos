(function () {
  'use strict';

  function absoluteUrl(pathOrUrl) {
    try {
      return new URL(pathOrUrl || window.location.href, window.location.origin).href;
    } catch (_) {
      return window.location.href;
    }
  }

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (_) {}
    }

    try {
      var area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      area.style.pointerEvents = 'none';
      document.body.appendChild(area);
      area.select();
      area.setSelectionRange(0, area.value.length);
      var ok = document.execCommand('copy');
      document.body.removeChild(area);
      return !!ok;
    } catch (_) {
      return false;
    }
  }

  function isMobileLike() {
    var ua = navigator.userAgent || '';
    return /Android|iPhone|iPad|iPod/i.test(ua) ||
      (window.matchMedia && window.matchMedia('(pointer: coarse)').matches && window.innerWidth < 900);
  }

  function popup(url) {
    var win = window.open(url, '_blank', 'noopener,noreferrer,width=720,height=680');
    if (!win) window.location.href = url;
  }

  function ensureDialog() {
    var existing = document.getElementById('mfhShareOverlay');
    if (existing) return existing;

    var overlay = document.createElement('div');
    overlay.id = 'mfhShareOverlay';
    overlay.setAttribute('aria-hidden', 'true');
    overlay.style.cssText = [
      'position:fixed', 'inset:0', 'z-index:2147483000',
      'background:rgba(15,23,42,.55)', 'display:none',
      'align-items:center', 'justify-content:center', 'padding:18px'
    ].join(';');

    overlay.innerHTML = `
      <div role="dialog" aria-modal="true" aria-labelledby="mfhShareTitle"
           style="width:min(460px,100%);background:#fff;border-radius:18px;box-shadow:0 24px 70px rgba(15,23,42,.35);overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:16px 18px;border-bottom:1px solid #f1f5f9;">
          <div>
            <div id="mfhShareTitle" style="font-size:1.05rem;font-weight:900;color:#831843;">Share this page</div>
            <div style="font-size:.76rem;color:#64748b;margin-top:2px;">Choose where you want to share the link.</div>
          </div>
          <button type="button" data-share-close aria-label="Close"
                  style="border:0;background:#f8fafc;color:#475569;width:34px;height:34px;border-radius:50%;font-size:20px;cursor:pointer;">×</button>
        </div>
        <div style="padding:15px 18px 8px;">
          <div id="mfhShareName" style="font-weight:800;color:#1e293b;margin-bottom:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"></div>
          <div id="mfhShareUrl" style="font-size:.78rem;color:#64748b;background:#f8fafc;border:1px solid #e2e8f0;padding:9px 10px;border-radius:9px;word-break:break-all;"></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;padding:10px 18px 18px;">
          <button type="button" data-share="facebook" style="padding:11px;border:1px solid #dbeafe;border-radius:10px;background:#eff6ff;color:#1d4ed8;font-weight:800;cursor:pointer;">Facebook</button>
          <button type="button" data-share="whatsapp" style="padding:11px;border:1px solid #dcfce7;border-radius:10px;background:#f0fdf4;color:#15803d;font-weight:800;cursor:pointer;">WhatsApp</button>
          <button type="button" data-share="telegram" style="padding:11px;border:1px solid #e0f2fe;border-radius:10px;background:#f0f9ff;color:#0369a1;font-weight:800;cursor:pointer;">Telegram</button>
          <button type="button" data-share="email" style="padding:11px;border:1px solid #f3e8ff;border-radius:10px;background:#faf5ff;color:#7e22ce;font-weight:800;cursor:pointer;">Email</button>
          <button type="button" data-share="copy" style="grid-column:1/-1;padding:12px;border:1px solid #fbcfe8;border-radius:10px;background:#fdf2f8;color:#be185d;font-weight:900;cursor:pointer;">🔗 Copy Link</button>
          <button type="button" data-share="native" style="display:none;grid-column:1/-1;padding:12px;border:0;border-radius:10px;background:#ec4899;color:#fff;font-weight:900;cursor:pointer;">More Apps…</button>
        </div>
      </div>`;

    document.body.appendChild(overlay);

    overlay.addEventListener('click', function (event) {
      if (event.target === overlay || event.target.closest('[data-share-close]')) close();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && overlay.style.display !== 'none') close();
    });
    return overlay;
  }

  var current = { title: '', url: '' };

  function close() {
    var overlay = document.getElementById('mfhShareOverlay');
    if (!overlay) return;
    overlay.style.display = 'none';
    overlay.setAttribute('aria-hidden', 'true');
  }

  function open(title, pathOrUrl) {
    var overlay = ensureDialog();
    current.title = title || document.title || 'Macleen\'s';
    current.url = absoluteUrl(pathOrUrl);

    overlay.querySelector('#mfhShareName').textContent = current.title;
    overlay.querySelector('#mfhShareUrl').textContent = current.url;
    var copyBtn = overlay.querySelector('[data-share="copy"]');
    copyBtn.textContent = '🔗 Copy Link';

    var nativeBtn = overlay.querySelector('[data-share="native"]');
    nativeBtn.style.display = (navigator.share && isMobileLike()) ? 'block' : 'none';

    overlay.style.display = 'flex';
    overlay.setAttribute('aria-hidden', 'false');

    overlay.querySelector('[data-share="facebook"]').onclick = function () {
      popup('https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(current.url));
    };
    overlay.querySelector('[data-share="whatsapp"]').onclick = function () {
      popup('https://wa.me/?text=' + encodeURIComponent(current.title + '\n' + current.url));
    };
    overlay.querySelector('[data-share="telegram"]').onclick = function () {
      popup('https://t.me/share/url?url=' + encodeURIComponent(current.url) + '&text=' + encodeURIComponent(current.title));
    };
    overlay.querySelector('[data-share="email"]').onclick = function () {
      window.location.href = 'mailto:?subject=' + encodeURIComponent(current.title) + '&body=' + encodeURIComponent(current.title + '\n\n' + current.url);
    };
    copyBtn.onclick = async function () {
      var ok = await copyText(current.url);
      if (ok) {
        copyBtn.textContent = '✓ Link Copied';
        setTimeout(function () { copyBtn.textContent = '🔗 Copy Link'; }, 1800);
      } else {
        window.prompt('Copy this link:', current.url);
      }
    };
    nativeBtn.onclick = async function () {
      try {
        await navigator.share({ title: current.title, url: current.url });
        close();
      } catch (err) {
        if (err && err.name === 'AbortError') return;
        nativeBtn.textContent = 'Could not open apps — use options above';
        setTimeout(function () { nativeBtn.textContent = 'More Apps…'; }, 2200);
      }
    };
  }

  window.MacleensShare = { open: open, close: close, copyText: copyText };
})();
