import { WebGPURenderer } from './webgpu_renderer';
import { connectAndSubscribe } from './flatir';

async function main(): Promise<void> {
  const canvas = document.getElementById('canvas') as HTMLCanvasElement;
  if (!canvas) return;

  const resize = () => {
    const dpr = window.devicePixelRatio ?? 1;
    canvas.width = Math.floor(canvas.clientWidth * dpr);
    canvas.height = Math.floor(canvas.clientHeight * dpr);
  };
  resize();
  window.addEventListener('resize', resize);

  const renderer = new WebGPURenderer();
  const ok = await renderer.init(canvas);
  if (!ok) {
    document.body.innerHTML = '<p style="color:#fff;padding:2rem">WebGPU not supported</p>';
    return;
  }

  connectAndSubscribe((packed) => renderer.setScene(packed));

  const loop = () => {
    renderer.render();
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

main();
