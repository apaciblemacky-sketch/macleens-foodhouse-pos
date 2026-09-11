/* Small reusable customer-to-cashier chat widget for the public portals.
 * Storefront chat can remain account-bound; Crafts and Digital use temporary guest threads.
 */
(function () {
  'use strict';

  function escapeText(value) {
    return String(value || '');
  }

  function init(options) {
    const root = document.getElementById(options.rootId);
    if (!root || root.dataset.chatReady) return;
    root.dataset.chatReady = '1';

    const panel = root.querySelector('[data-cashier-chat-panel]');
    const toggle = root.querySelector('[data-cashier-chat-toggle]');
    const close = root.querySelector('[data-cashier-chat-close]');
    const log = root.querySelector('[data-cashier-chat-log]');
    const input = root.querySelector('[data-cashier-chat-input]');
    const send = root.querySelector('[data-cashier-chat-send]');
    let knownCashierMessages = new Set();
    let loaded = false;
    let loginRequired = false;
    const portal = String(options.portal || '').trim().toUpperCase();
    const portalQuery = portal ? ('?portal=' + encodeURIComponent(portal)) : '';

    function addBubble(kind, text) {
      const bubble = document.createElement('div');
      bubble.className = 'cashier-chat-message ' + (kind || 'system').toLowerCase();
      bubble.textContent = escapeText(text);
      log.appendChild(bubble);
      log.scrollTop = log.scrollHeight;
      return bubble;
    }

    function showLoginPrompt(message) {
      loginRequired = true;
      log.innerHTML = '';
      addBubble('system', message || 'Please log in first so we can reply to you here.');
      const link = document.createElement('a');
      link.href = '/portal/login';
      link.className = 'cashier-chat-login';
      link.textContent = 'Log in to Chat with us';
      log.appendChild(link);
      input.disabled = true;
      send.disabled = true;
    }

    function togglePanel(force) {
      const open = force === undefined ? !panel.classList.contains('open') : Boolean(force);
      panel.classList.toggle('open', open);
      if (open) {
        if (!loginRequired) loadMessages();
        if (!loginRequired) input.focus();
      }
    }

    async function loadMessages() {
      try {
        const response = await fetch('/api/customer-chat/messages' + portalQuery, {cache: 'no-store'});
        const data = await response.json().catch(function () { return {}; });
        if (response.status === 401 || response.status === 403) {
          showLoginPrompt(data.message);
          return;
        }
        if (!response.ok || !data.success) return;
        log.innerHTML = '';
        let hasNewCashierReply = false;
        (data.messages || []).forEach(function (message) {
          const isRemote = message.sender_type === 'CASHIER';
          if (loaded && isRemote && !knownCashierMessages.has(String(message.id))) hasNewCashierReply = true;
          if (isRemote) knownCashierMessages.add(String(message.id));
          addBubble(message.sender_type || 'SYSTEM', message.body || '');
        });
        loaded = true;
        if (hasNewCashierReply && !panel.classList.contains('open')) togglePanel(true);
      } catch (_) {
        // A transient connection failure should not erase the open chat.
      }
    }

    async function sendMessage() {
      if (loginRequired) return showLoginPrompt();
      const message = input.value.trim();
      if (!message) return;
      input.value = '';
      send.disabled = true;
      try {
        const response = await fetch('/api/customer-chat/messages', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({message: message, portal: portal})
        });
        const data = await response.json().catch(function () { return {}; });
        if (response.status === 401 || response.status === 403) return showLoginPrompt(data.message);
        if (!response.ok || !data.success) addBubble('system', data.message || 'Your message could not be sent. Please try again.');
        else loadMessages();
      } catch (_) {
        addBubble('system', 'Your message could not be sent. Please check your connection.');
      } finally {
        if (!loginRequired) send.disabled = false;
      }
    }

    toggle.addEventListener('click', function () { togglePanel(); });
    close.addEventListener('click', function () { togglePanel(false); });
    send.addEventListener('click', sendMessage);
    input.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });
    window.setInterval(function () {
      if (panel.classList.contains('open') && !loginRequired) loadMessages();
    }, 3000);
  }

  window.MacleensCashierChat = {init: init};
}());
