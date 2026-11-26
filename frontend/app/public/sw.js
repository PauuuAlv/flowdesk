/*
 * Service worker de Flowdesk para Web Push (W3C Push API + VAPID).
 *
 * El backend cifra cada mensaje para esta suscripción y lo entrega mediante el
 * servicio push del navegador. Aquí se muestra la notificación del sistema y,
 * al hacer clic, se abre (o enfoca) Flowdesk en la ruta indicada.
 */
const DEFAULT_URL = '/panel';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { body: event.data ? event.data.text() : '' };
  }
  const title = data.title || 'Flowdesk';
  const options = {
    body: data.body || '',
    tag: data.tag || undefined,
    icon: '/favicon.ico',
    badge: '/favicon.ico',
    lang: 'es-MX',
    renotify: Boolean(data.tag),
    requireInteraction: data.type === 'activity_overdue' || data.type === 'activity_reminder',
    data: { url: data.url || DEFAULT_URL, id: data.id || null },
  };
  event.waitUntil(
    Promise.all([
      self.registration.showNotification(title, options),
      // Las pestañas abiertas actualizan su campana sin esperar al siguiente sondeo.
      self.clients
        .matchAll({ type: 'window', includeUncontrolled: true })
        .then((clients) => clients.forEach((client) => client.postMessage({ type: 'flowdesk:push', payload: data }))),
    ]),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = new URL(event.notification.data?.url || DEFAULT_URL, self.location.origin);
  // Solo rutas del propio sitio.
  const url = target.origin === self.location.origin ? target.href : new URL(DEFAULT_URL, self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((client) => new URL(client.url).origin === self.location.origin);
      if (existing) {
        existing.postMessage({ type: 'flowdesk:navigate', url: target.pathname + target.search + target.hash });
        return existing.focus();
      }
      return self.clients.openWindow(url);
    }),
  );
});

// El navegador puede rotar la suscripción; se vuelve a registrar en el backend
// la próxima vez que el usuario abra Flowdesk (PushNotificationService.sync).
self.addEventListener('pushsubscriptionchange', () => {});
