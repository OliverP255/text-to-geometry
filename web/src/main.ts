import { WebGPURenderer } from './webgpu_renderer';
import { connectAndSubscribe } from './flatir';
import { sceneServerBaseUrl } from './sceneServer';
import type { PackedFlatIR, WGSLSdfScene } from './types';

const DEFAULT_WGSL_SCENE: WGSLSdfScene = {
  type: 'wgsl-sdf',
  code: 'fn map(p: vec3f) -> f32 { return sdSphere(p, 1.0); }',
};

function isWgslSdfScene(x: unknown): x is WGSLSdfScene {
  return (
    typeof x === 'object' &&
    x !== null &&
    (x as WGSLSdfScene).type === 'wgsl-sdf' &&
    typeof (x as WGSLSdfScene).code === 'string'
  );
}

function setStatus(html: string): void {
  const el = document.getElementById('status');
  if (el) el.innerHTML = html;
}

function escapeHtmlText(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Prompt bar ──────────────────────────────────────────────────

type ChatResponse = { ok?: boolean; error?: string; code?: string };

function initPromptBar(renderer: WebGPURenderer | null): void {
  const bar = document.getElementById('prompt-bar')!;
  const input = document.getElementById('prompt-input') as HTMLInputElement;
  const send = document.getElementById('prompt-send') as HTMLButtonElement;

  let busy = false;
  const base = sceneServerBaseUrl();

  async function handleSend(): Promise<void> {
    const text = input.value.trim();
    if (!text || busy) return;

    busy = true;
    send.disabled = true;
    bar.classList.add('loading');
    input.placeholder = 'Generating…';

    try {
      const resp = await fetch(`${base}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: text }),
      });
      const raw = await resp.text();
      let data: ChatResponse = {};
      try {
        data = raw ? (JSON.parse(raw) as ChatResponse) : {};
      } catch {
        input.placeholder = `Server error (${resp.status})`;
        setStatus(`<span class="err">chat: bad JSON (${resp.status})</span>`);
        setTimeout(() => { input.placeholder = 'Describe a shape…'; }, 4000);
        return;
      }

      if (resp.ok && data.ok && typeof data.code === 'string' && data.code.trim()) {
        input.value = '';
        input.placeholder = 'Describe a shape…';
        const scene: WGSLSdfScene = { type: 'wgsl-sdf', code: data.code };
        if (renderer) {
          renderer.setWgslScene(scene);
          setStatus(`<span class="ok">scene</span> · wgsl (${data.code.length} chars)`);
        } else {
          setStatus(
            `<span class="ok">scene ok</span> · wgsl (${data.code.length} chars) — <span class="err">no WebGPU preview</span>`,
          );
        }
      } else {
        const msg = data.error || `Request failed (${resp.status})`;
        input.placeholder = msg.slice(0, 80);
        setStatus(`<span class="err">${escapeHtmlText(msg)}</span>`);
        setTimeout(() => { input.placeholder = 'Describe a shape…'; }, 6000);
      }
    } catch {
      input.placeholder = `Can’t reach ${base} — run: python3 server.py`;
      setStatus(`<span class="err">no server at ${base}</span>`);
      setTimeout(() => { input.placeholder = 'Describe a shape…'; }, 6000);
    } finally {
      busy = false;
      send.disabled = false;
      bar.classList.remove('loading');
      input.focus();
    }
  }

  send.addEventListener('click', handleSend);
  input.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  });
}

// ── Renderer bootstrap ──────────────────────────────────────────

async function main(): Promise<void> {
  const canvas = document.getElementById('canvas') as HTMLCanvasElement;
  if (!canvas) {
    setStatus('<span class="err">canvas not found</span>');
    return;
  }

  const renderer = new WebGPURenderer();

  setStatus('initialising WebGPU…');
  const ok = await renderer.init(canvas);
  if (!ok) {
    setStatus('<span class="err">WebGPU not supported</span> · prompt bar still talks to server');
    initPromptBar(null);
    return;
  }

  let resizeTimer: ReturnType<typeof setTimeout>;
  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio ?? 1, 2);
    canvas.width = Math.floor(canvas.clientWidth * dpr);
    canvas.height = Math.floor(canvas.clientHeight * dpr);
    renderer.handleResize();
  };
  resize();
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 50);
  });

  renderer.setWgslScene(DEFAULT_WGSL_SCENE);
  setStatus('<span class="ok">gpu ready</span> · connecting…');

  initPromptBar(renderer);

  connectAndSubscribe(
    (data) => {
      if (isWgslSdfScene(data)) {
        renderer.setWgslScene(data);
        setStatus(`<span class="ok">live</span> · wgsl (${data.code.length} chars)`);
      } else {
        renderer.setScene(data as PackedFlatIR);
        const n = (data as PackedFlatIR).instrs?.length ?? 0;
        setStatus(`<span class="ok">live</span> · ${n} ops (flatir)`);
      }
    },
    () => setStatus('<span class="ok">connected</span> · waiting for scene…'),
    (err) => setStatus(`<span class="err">socket: ${err.message}</span>`),
  );

  const loop = () => {
    renderer.render();
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

main();
