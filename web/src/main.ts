import { WebGPURenderer } from './webgpu_renderer';
import { connectAndSubscribe, getSocket } from './flatir';
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

// -- Prompt bar ---------------------------------------------------

let hasScene = false;
let lastCode: string | null = null;

function initPromptBar(renderer: WebGPURenderer | null): void {
  const input = document.getElementById('prompt-input') as HTMLInputElement;
  const send = document.getElementById('prompt-send') as HTMLButtonElement;
  const bar = document.getElementById('prompt-bar')!;

  let busy = false;

  function handleSend(): void {
    const text = input.value.trim();
    if (!text || busy) return;

    const socket = getSocket();
    if (!socket?.connected) {
      setStatus('<span class="err">not connected to server</span>');
      return;
    }

    busy = true;
    send.disabled = true;
    bar.classList.add('loading');

    const isRefine = hasScene;
    const action = isRefine ? 'refining' : 'generating';
    input.placeholder = action.charAt(0).toUpperCase() + action.slice(1) + '\u2026';
    setStatus(`<span class="ok">${action}\u2026</span>`);

    const cleanup = () => {
      busy = false;
      send.disabled = false;
      bar.classList.remove('loading');
      input.focus();
    };

    socket.once('chat_done', (data: { code?: string }) => {
      hasScene = true;
      if (data?.code) {
        lastCode = data.code;
        console.log('WGSL code:\n', data.code);
        // Show export/print buttons
        const exportBtn = document.getElementById('export-stl') as HTMLButtonElement;
        const printBtn = document.getElementById('print-btn') as HTMLButtonElement;
        if (exportBtn) exportBtn.style.display = 'flex';
        if (printBtn) printBtn.style.display = 'flex';
        fetchSizePreview(data.code);
      }
      input.value = '';
      input.placeholder = 'Refine: "make it smoother", "add twist", or new: "/new gyroid"';
      cleanup();
    });

    socket.once('chat_error', (data: { error?: string }) => {
      const msg = data.error || 'Generation failed';
      input.placeholder = msg.slice(0, 80);
      setStatus(`<span class="err">${escapeHtmlText(msg)}</span>`);
      setTimeout(() => {
        input.placeholder = hasScene
          ? 'Refine or type /new for a fresh shape\u2026'
          : 'Describe a shape\u2026';
      }, 4000);
      cleanup();
    });

    if (text.startsWith('/new ')) {
      hasScene = false;
      socket.emit('chat', { prompt: text.slice(5).trim() });
    } else if (isRefine) {
      socket.emit('refine', { instruction: text });
    } else {
      socket.emit('chat', { prompt: text });
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

// -- Export button ------------------------------------------------

// Request size preview when scene updates
async function fetchSizePreview(code: string): Promise<void> {
  const dimensionsEl = document.getElementById('dimensions');
  try {
    const resp = await fetch('/export/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    if (resp.ok) {
      const data = await resp.json();
      const [w, h, d] = data.dimensions_mm as [number, number, number];
      if (dimensionsEl) {
        dimensionsEl.textContent = `${w.toFixed(0)} \u00d7 ${h.toFixed(0)} \u00d7 ${d.toFixed(0)} mm`;
        dimensionsEl.style.display = 'block';
      }
    }
  } catch {
    // Ignore preview errors
  }
}

function initExportButton(): void {
  const exportBtn = document.getElementById('export-stl') as HTMLButtonElement;

  if (!exportBtn) return;

  // Handle export click
  exportBtn.addEventListener('click', async () => {
    if (!lastCode) return;

    exportBtn.disabled = true;

    try {
      const response = await fetch('/export/stl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: lastCode }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ error: 'Export failed' }));
        throw new Error(errData.error || 'Export failed');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'shape.stl';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setStatus(`<span class="err">${escapeHtmlText(msg)}</span>`);
    } finally {
      exportBtn.disabled = false;
    }
  });
}

// -- Renderer bootstrap -------------------------------------------

async function main(): Promise<void> {
  const canvas = document.getElementById('canvas') as HTMLCanvasElement;
  if (!canvas) {
    setStatus('<span class="err">canvas not found</span>');
    return;
  }

  const renderer = new WebGPURenderer();

  setStatus('initialising WebGPU\u2026');
  const ok = await renderer.init(canvas);
  if (!ok) {
    setStatus('<span class="err">WebGPU not supported</span>');
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
  setStatus('<span class="ok">gpu ready</span> \u00b7 connecting\u2026');

  initPromptBar(renderer);

  connectAndSubscribe(
    (data) => {
      if (isWgslSdfScene(data)) {
        renderer.setWgslScene(data);
        setStatus(`<span class="ok">live</span> \u00b7 wgsl (${data.code.length} chars)`);
      } else {
        renderer.setScene(data as PackedFlatIR);
        const n = (data as PackedFlatIR).instrs?.length ?? 0;
        setStatus(`<span class="ok">live</span> \u00b7 ${n} ops (flatir)`);
      }
    },
    () => setStatus('<span class="ok">connected</span> \u00b7 waiting for scene\u2026'),
    (err) => setStatus(`<span class="err">socket: ${err.message}</span>`),
  );

  initExportButton();

  const loop = () => {
    renderer.render();
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

main();
