// Minimal service worker — just enough to make the app installable
// (Android "Add to Home Screen" needs a registered SW with a fetch handler).
// No caching yet; add offline caching here later if desired.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
