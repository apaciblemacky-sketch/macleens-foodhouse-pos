(function () {
  'use strict';
  if (window.MacleensLiveUI) return;

  const LIVE_SELECTOR = 'script[data-macleens-live]';
  let busy = false;
  document.querySelectorAll('head style,head link[rel="stylesheet"]').forEach(function (node) {
    node.setAttribute('data-live-page-head', '1');
  });

  function sameOrigin(url) {
    try { return new URL(url, location.href).origin === location.origin; }
    catch (_) { return false; }
  }

  function canHandleUrl(url) {
    const parsed = new URL(url, location.href);
    if (parsed.origin !== location.origin) return false;
    if (/\.(?:pdf|zip|csv|xlsx?|docx?|png|jpe?g|gif|webp|svg)$/i.test(parsed.pathname)) return false;
    if (parsed.pathname.startsWith('/static/') || parsed.pathname.startsWith('/api/')) return false;
    return true;
  }

  function formRequestSpec(form, submitter) {
    // Read the actual HTML attributes. DOM properties on a submit button can
    // report browser defaults (GET/current URL) when no override was declared,
    // which can turn an original POST form into a 405 request.
    const buttonAction = submitter ? submitter.getAttribute('formaction') : '';
    const buttonMethod = submitter ? submitter.getAttribute('formmethod') : '';
    const rawAction = buttonAction || form.getAttribute('action') || location.href;
    const rawMethod = buttonMethod || form.getAttribute('method') || 'GET';
    return {
      action: new URL(rawAction, location.href).href,
      method: String(rawMethod).trim().toUpperCase() || 'GET'
    };
  }

  function hardSubmit(form, submitter, spec) {
    spec = spec || formRequestSpec(form, submitter);
    form.dataset.liveBypass = '1';
    form.setAttribute('action', spec.action);
    form.setAttribute('method', spec.method);
    if (submitter && submitter.name) {
      const hidden = document.createElement('input');
      hidden.type = 'hidden'; hidden.name = submitter.name; hidden.value = submitter.value;
      form.appendChild(hidden);
    }
    HTMLFormElement.prototype.submit.call(form);
  }

  function loading(active) {
    let bar = document.getElementById('macleens-live-progress');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'macleens-live-progress';
      bar.setAttribute('aria-hidden', 'true');
      bar.style.cssText = 'position:fixed;z-index:2147483647;left:0;top:0;height:4px;width:0;background:linear-gradient(90deg,#ec4899,#0891b2);box-shadow:0 0 8px rgba(8,145,178,.5);transition:width .2s ease,opacity .2s ease;opacity:0;pointer-events:none';
      document.documentElement.appendChild(bar);
    }
    if (active) {
      bar.style.opacity = '1'; bar.style.width = '72%';
      document.documentElement.setAttribute('aria-busy', 'true');
    } else {
      bar.style.width = '100%';
      setTimeout(function () { bar.style.opacity = '0'; bar.style.width = '0'; }, 180);
      document.documentElement.removeAttribute('aria-busy');
    }
  }

  function copyHead(nextDoc) {
    document.querySelectorAll('head [data-live-page-head]').forEach(function (node) { node.remove(); });
    nextDoc.querySelectorAll('head style,head link[rel="stylesheet"]').forEach(function (node) {
      const clone = node.cloneNode(true);
      clone.setAttribute('data-live-page-head', '1');
      document.head.appendChild(clone);
    });
    const nextDescription = nextDoc.querySelector('meta[name="description"]');
    let currentDescription = document.querySelector('meta[name="description"]');
    if (nextDescription) {
      if (!currentDescription) { currentDescription = document.createElement('meta'); currentDescription.name = 'description'; document.head.appendChild(currentDescription); }
      currentDescription.content = nextDescription.content || '';
    }
  }

  function runBodyScripts(root) {
    const scripts = Array.from(root.querySelectorAll('script'));
    scripts.forEach(function (oldScript) {
      if (oldScript.matches(LIVE_SELECTOR) || (oldScript.src && /\/static\/live-ui\.js/.test(oldScript.src))) {
        oldScript.remove(); return;
      }
      const fresh = document.createElement('script');
      Array.from(oldScript.attributes).forEach(function (attr) { fresh.setAttribute(attr.name, attr.value); });
      if (oldScript.src) fresh.async = false;
      else fresh.textContent = oldScript.textContent;
      oldScript.replaceWith(fresh);
    });
  }

  function showError(message) {
    let toast = document.getElementById('macleens-live-error');
    if (!toast) {
      toast = document.createElement('div'); toast.id = 'macleens-live-error';
      toast.style.cssText = 'position:fixed;z-index:2147483647;right:16px;bottom:16px;max-width:380px;background:#991b1b;color:#fff;padding:12px 16px;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.25);font:600 14px Arial';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    setTimeout(function () { if (toast) toast.remove(); }, 5000);
  }

  async function applyHtml(html, finalUrl, options) {
    const nextDoc = new DOMParser().parseFromString(html, 'text/html');
    if (!nextDoc.body || !nextDoc.title) throw new Error('The server returned an incomplete page.');
    const oldScroll = window.scrollY;
    copyHead(nextDoc);
    document.title = nextDoc.title;
    const newBody = document.importNode(nextDoc.body, true);
    document.body.replaceWith(newBody);
    runBodyScripts(document.body);
    if (options && options.history === 'push' && finalUrl !== location.href) history.pushState({ live: true }, '', finalUrl);
    else if (options && options.history === 'replace' && finalUrl !== location.href) history.replaceState({ live: true }, '', finalUrl);
    if (options && options.keepScroll) window.scrollTo(0, oldScroll);
    else if (new URL(finalUrl, location.href).hash) {
      const targetId = decodeURIComponent(new URL(finalUrl, location.href).hash.slice(1));
      requestAnimationFrame(function () {
        const target = document.getElementById(targetId);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        else window.scrollTo(0, 0);
      });
    } else window.scrollTo(0, 0);
    document.dispatchEvent(new CustomEvent('macleens:page-updated', { detail: { url: finalUrl } }));
  }

  async function visit(url, options) {
    if (busy || !canHandleUrl(url)) { location.href = url; return; }
    const requestedUrl = new URL(url, location.href);
    const requestedHash = requestedUrl.hash;
    busy = true; loading(true);
    try {
      const response = await fetch(url, { credentials: 'same-origin', headers: { 'X-Macleens-Live': '1' } });
      const type = response.headers.get('content-type') || '';
      if (!response.ok || !type.includes('text/html')) throw new Error('Page could not be loaded (' + response.status + ').');
      const finalUrl = new URL(response.url, location.href);
      if (requestedHash && finalUrl.origin === requestedUrl.origin && finalUrl.pathname === requestedUrl.pathname) {
        finalUrl.hash = requestedHash;
      }
      await applyHtml(await response.text(), finalUrl.href, { history: options && options.replace ? 'replace' : 'push' });
    } catch (error) {
      showError(error.message || 'The page could not be updated.');
    } finally { busy = false; loading(false); }
  }

  async function submitForm(form, submitter) {
    if (busy) return;
    const spec = formRequestSpec(form, submitter);
    const action = spec.action;
    const method = spec.method;
    if (!sameOrigin(action) || !canHandleUrl(action) || form.dataset.noLive !== undefined || form.target) {
      hardSubmit(form, submitter, spec); return;
    }
    busy = true; loading(true);
    const button = submitter || form.querySelector('[type="submit"],button:not([type])');
    const previousText = button ? button.textContent : '';
    if (button) { button.disabled = true; button.textContent = method === 'GET' ? 'Loading…' : 'Saving…'; }
    try {
      const data = new FormData(form);
      if (submitter && submitter.name) data.append(submitter.name, submitter.value);
      let url = action;
      const fetchOptions = { method: method, credentials: 'same-origin', headers: { 'X-Macleens-Live': '1' } };
      if (method === 'GET') {
        const parsed = new URL(action, location.href);
        data.forEach(function (value, key) { if (typeof value === 'string') parsed.searchParams.set(key, value); });
        url = parsed.href;
      } else fetchOptions.body = data;
      const response = await fetch(url, fetchOptions);
      if (response.status === 405) {
        // A legacy or browser-specific form cannot safely use the live layer.
        // No mutation occurred on a 405, so return it to its exact original
        // submission behavior instead of leaving the user with an error toast.
        hardSubmit(form, submitter, spec);
        return;
      }
      const type = response.headers.get('content-type') || '';
      if (type.includes('application/json')) {
        const payload = await response.json();
        if (!response.ok || payload.success === false) throw new Error(payload.message || 'The action failed.');
        document.dispatchEvent(new CustomEvent('macleens:action-complete', { detail: payload }));
      } else {
        if (!response.ok || !type.includes('text/html')) throw new Error('The server could not complete this action (' + response.status + ').');
        const finalUrl = response.url || location.href;
        await applyHtml(await response.text(), finalUrl, { history: finalUrl === location.href ? null : 'replace', keepScroll: finalUrl === location.href });
      }
    } catch (error) {
      if (button && document.contains(button)) { button.disabled = false; button.textContent = previousText; }
      showError(error.message || 'The action could not be completed.');
    } finally { busy = false; loading(false); }
  }

  document.addEventListener('click', function (event) {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (link.target || link.download || link.dataset.noLive !== undefined) return;
    const href = link.getAttribute('href') || '';
    if (!href || href.startsWith('#') || /^(?:mailto:|tel:|javascript:)/i.test(href) || !canHandleUrl(link.href)) return;
    event.preventDefault(); visit(link.href);
  });

  document.addEventListener('submit', function (event) {
    if (event.defaultPrevented) return;
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.dataset.liveBypass === '1') return;
    event.preventDefault(); submitForm(form, event.submitter);
  });

  window.addEventListener('popstate', function () { visit(location.href, { replace: true }); });

  window.MacleensLiveUI = {
    visit: visit,
    refresh: function () { return visit(location.href, { replace: true }); },
    submit: submitForm
  };
})();
