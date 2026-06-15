/* Static self-destroying service worker.
   The app no longer ships a service worker (vite-plugin-pwa was removed). This
   file stays at /sw.js only so browsers that still have an OLD service worker
   registered will, on their next update check, fetch this, unregister it, clear
   all caches, and reload — leaving no SW. Because index.html no longer registers
   any SW, nothing re-registers afterwards. */
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    try { await self.registration.unregister() } catch (e) { /* ignore */ }
    try {
      const keys = await caches.keys()
      await Promise.all(keys.map((k) => caches.delete(k)))
    } catch (e) { /* ignore */ }
    const clients = await self.clients.matchAll({ type: 'window' })
    clients.forEach((c) => { try { c.navigate(c.url) } catch (e) { /* ignore */ } })
  })())
})
