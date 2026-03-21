import { io } from 'socket.io-client';
import type { PackedFlatIR } from './types';

/** Connect to WebSocket and subscribe to scene updates. On connect, server emits "scene" with packed data. */
export function connectAndSubscribe(callback: (packed: PackedFlatIR) => void): void {
  const url = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5001';
  const socket = io(url, { path: '/socket.io', transports: ['websocket'] });
  socket.on('connect', () => {
    if (typeof window !== 'undefined' && 'console' in window) {
      console.log('[flatir] socket connected');
    }
  });
  socket.on('scene', (packed: PackedFlatIR) => {
    if (typeof window !== 'undefined' && 'console' in window) {
      console.log('[flatir] scene received', packed?.instrs?.length ?? 0, 'instrs');
    }
    callback(packed);
  });
  socket.on('connect_error', (err: Error) => {
    if (typeof window !== 'undefined' && 'console' in window) {
      console.error('[flatir] socket connect_error', err);
    }
  });
}
