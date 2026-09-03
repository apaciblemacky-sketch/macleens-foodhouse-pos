self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(clients.claim());
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    fetch(e.request).catch(() => {
      return new Response('Network offline. Please reconnect.');
    })
  );
});

self.addEventListener('push', (event) => {
  let payload = {};
  try { payload = event.data ? event.data.json() : {}; } catch (_) { payload = {body: event.data ? event.data.text() : ''}; }
  const title = payload.title || "Macleen's Community";
  const url = payload.url && String(payload.url).startsWith('/') ? payload.url : '/community';
  event.waitUntil(self.registration.showNotification(title, {
    body: payload.body || 'A new local update is waiting.',
    icon: '/static/logo.png',
    badge: '/static/logo.png',
    tag: payload.tag || 'macleens-community',
    renotify: true,
    data: {url},
  }));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = event.notification.data?.url || '/community';
  event.waitUntil(clients.matchAll({type: 'window', includeUncontrolled: true}).then((windows) => {
    const existing = windows.find(item => new URL(item.url).pathname === target);
    return existing ? existing.focus() : clients.openWindow(target);
  }));
});
