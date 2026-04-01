import { io } from 'socket.io-client';
import type { SceneData } from './types';
import { sceneServerBaseUrl } from './sceneServer';

export function connectAndSubscribe(
  onScene: (data: SceneData) => void,
  onConnect?: () => void,
  onError?: (err: Error) => void,
): void {
  const socket = io(sceneServerBaseUrl(), {
    path: '/socket.io',
    transports: ['websocket', 'polling'],
  });
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
