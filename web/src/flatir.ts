import { io, type Socket } from 'socket.io-client';
import type { SceneData } from './types';
import { sceneServerBaseUrl } from './sceneServer';

let _socket: Socket | null = null;

export function getSocket(): Socket | null {
  return _socket;
}

export function connectAndSubscribe(
  onScene: (data: SceneData) => void,
  onConnect?: () => void,
  onError?: (err: Error) => void,
): void {
  const socket = io(sceneServerBaseUrl(), {
    path: '/socket.io',
    transports: ['websocket', 'polling'],
  });
  _socket = socket;
  socket.on('connect', () => {
    onConnect?.();
  });
  socket.on('scene', (data: SceneData) => {
    onScene(data);
  });
  socket.on('connect_error', (err: Error) => {
    onError?.(err);
  });
}
