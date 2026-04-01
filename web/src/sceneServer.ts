/**
 * Base URL for Flask + Socket.IO (port 5001). In Vite dev the page is on another
 * origin, so we talk to the scene server explicitly. Production is served from Flask.
 */
export function sceneServerBaseUrl(): string {
  const fromEnv = (import.meta.env.VITE_SCENE_SERVER as string | undefined)?.trim();
  if (fromEnv) return fromEnv.replace(/\/$/, '');
  if (import.meta.env.DEV) return 'http://127.0.0.1:5001';
  if (typeof window !== 'undefined') return window.location.origin;
  return 'http://127.0.0.1:5001';
}
