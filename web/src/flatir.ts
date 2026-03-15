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

/** Connect to WebSocket and subscribe to scene updates. On connect, server emits "scene" with packed data. On connect_error, calls callback with defaultScene(). */
export function connectAndSubscribe(callback: (packed: PackedFlatIR) => void): void {
  const socket = io({ path: '/socket.io', transports: ["websocket"] });
  socket.on('scene', (packed: PackedFlatIR) => callback(packed));
  socket.on('connect_error', () => callback(defaultScene()));
}
