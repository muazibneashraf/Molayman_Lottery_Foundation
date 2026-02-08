/*
  Stub service worker file.
  Some browsers/extensions request /firebase-messaging-sw.js by default.
  We serve a no-op SW to avoid 404s without enabling push messaging.
*/

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
