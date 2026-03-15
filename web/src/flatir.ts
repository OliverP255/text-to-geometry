import { io } from 'socket.io-client';
import type { PackedFlatIR } from './types';

/** Default scene: single sphere at origin when backend unavailable. */
export function defaultScene(): PackedFlatIR {
  return {
    instrs: [{ op: 0, arg0: 0, arg1: 0, constIdx: 0 }],
    transforms: [0, 0, 0, 0, 1, 1, 1, 1],
    spheres: [1, 0, 0, 0],
    boxes: [],
    planes: [],
    rootTemp: 0,
  };
}

export async function fetchScene(url = '/scene'): Promise<PackedFlatIR> {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as PackedFlatIR;
  } catch {
    return defaultScene();
  }
}

/** Subscribe to scene updates via WebSocket. On scene_updated, fetches GET /scene and calls callback. */
export function subscribeToSceneUpdates(callback: (packed: PackedFlatIR) => void): void {
  const socket = io({ path: '/socket.io' });
  socket.on('scene_updated', async () => {
    const packed = await fetchScene();
    callback(packed);
  });
}
