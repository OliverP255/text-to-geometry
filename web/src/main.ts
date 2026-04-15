import { WebGPURenderer } from './webgpu_renderer';
import { BRepRenderer } from './brep_renderer';
import { connectAndSubscribe, getSocket } from './flatir';
import type { PackedFlatIR, WGSLSdfScene, BRepMeshScene } from './types';

const AUTH_TOKEN_KEY = 't2g_auth_token';
const AUTH_EMAIL_KEY = 't2g_user_email';

const DEFAULT_WGSL_SCENE: WGSLSdfScene = {
  type: 'wgsl-sdf',
  code: 'fn sceneEval(p: vec3f) -> f32 { return sdSphere(p, 1.0); }',
};

function isWgslSdfScene(x: unknown): x is WGSLSdfScene {
  return (
    typeof x === 'object' &&
    x !== null &&
    (x as WGSLSdfScene).type === 'wgsl-sdf' &&
    typeof (x as WGSLSdfScene).code === 'string'
  );
}

function isBRepMeshScene(x: unknown): x is BRepMeshScene {
  return (
    typeof x === 'object' &&
    x !== null &&
    (x as BRepMeshScene).type === 'brep-mesh' &&
    Array.isArray((x as BRepMeshScene).vertices)
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

/** Parse JSON from Flask; if the dev server returns HTML (e.g. missing /api proxy), explain. */
async function parseApiJson<T>(r: Response, label: string): Promise<T> {
  const text = await r.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    const looksHtml = /^\s*</.test(text);
    throw new Error(
      looksHtml
        ? `${label}: got HTML instead of JSON (HTTP ${r.status}). Start the scene server on :5001 and ensure Vite proxies /api.`
        : `${label}: invalid JSON (HTTP ${r.status})`,
    );
  }
}

// -- Prompt bar ---------------------------------------------------

let hasScene = false;
let lastCode: string | null = null;
let lastBrepCode: string | null = null;
let currentAgent: 'sdf' | 'brep' = 'sdf';
/** Matches API `geometry_kind`: wgsl-sdf | brep */
let lastSceneKind: 'wgsl-sdf' | 'brep' = 'wgsl-sdf';

function getStoredToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

function setAuthToken(token: string | null, email?: string | null): void {
  try {
    if (token) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
      if (email) localStorage.setItem(AUTH_EMAIL_KEY, email);
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(AUTH_EMAIL_KEY);
    }
  } catch {
    /* ignore */
  }
  syncAuthBar();
}

function syncAuthBar(): void {
  const label = document.getElementById('auth-label');
  const btnLogin = document.getElementById('auth-open-login') as HTMLButtonElement | null;
  const btnReg = document.getElementById('auth-open-register') as HTMLButtonElement | null;
  const btnOut = document.getElementById('auth-signout') as HTMLButtonElement | null;
  const tok = getStoredToken();
  let email = '';
  try {
    email = localStorage.getItem(AUTH_EMAIL_KEY) || '';
  } catch {
    /* ignore */
  }
  if (label) {
    label.textContent = tok ? (email ? email : 'Signed in') : 'Not signed in';
  }
  if (btnLogin) btnLogin.style.display = tok ? 'none' : 'inline-block';
  if (btnReg) btnReg.style.display = tok ? 'none' : 'inline-block';
  if (btnOut) btnOut.style.display = tok ? 'inline-block' : 'none';
}

function initPromptBar(
  sdfRenderer: WebGPURenderer | null,
  brepRenderer: BRepRenderer | null
): void {
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

    // Check for agent selection prefixes
    let promptText = text;
    let agentType = currentAgent;

    if (text.startsWith('/brep ')) {
      agentType = 'brep';
      promptText = text.slice(6).trim();
      currentAgent = 'brep';
    } else if (text.startsWith('/sdf ')) {
      agentType = 'sdf';
      promptText = text.slice(5).trim();
      currentAgent = 'sdf';
    } else if (text.startsWith('/new ')) {
      // /new resets scene, use current agent
      promptText = text.slice(5).trim();
      hasScene = false;
    }

    busy = true;
    send.disabled = true;
    bar.classList.add('loading');

    const isRefine = hasScene && !text.startsWith('/new ');
    const action = isRefine ? 'refining' : 'generating';
    const agentLabel = agentType === 'brep' ? 'B-Rep' : 'SDF';
    input.placeholder = `${action} (${agentLabel})\u2026`;
    setStatus(`<span class="ok">${action} ${agentLabel}\u2026</span>`);

    const cleanup = () => {
      busy = false;
      send.disabled = false;
      bar.classList.remove('loading');
      input.focus();
    };

    socket.once('chat_done', (data: { code?: string; type?: string }) => {
      hasScene = true;
      const isBrep = data?.type === 'brep' || agentType === 'brep';
      lastSceneKind = isBrep ? 'brep' : 'wgsl-sdf';

      if (data?.code) {
        if (isBrep) {
          lastBrepCode = data.code;
        } else {
          lastCode = data.code;
        }
        console.log(`${isBrep ? 'CadQuery' : 'WGSL'} code:\n`, data.code);

        // Show export/print buttons
        const exportBtn = document.getElementById('export-stl') as HTMLButtonElement;
        const printBtn = document.getElementById('print-btn') as HTMLButtonElement;
        if (exportBtn) exportBtn.style.display = 'flex';
        if (printBtn) printBtn.style.display = 'flex';

        // Fetch size preview for the appropriate agent
        if (isBrep && lastBrepCode) {
          fetchBrepSizePreview(lastBrepCode);
        } else if (lastCode) {
          fetchSizePreview(lastCode);
        }
      }
      input.value = '';
      input.placeholder = 'Refine: "make it larger", "add holes", or /brep for CAD mode';
      cleanup();
    });

    socket.once('chat_error', (data: { error?: string }) => {
      const msg = data.error || 'Generation failed';
      input.placeholder = msg.slice(0, 80);
      setStatus(`<span class="err">${escapeHtmlText(msg)}</span>`);
      setTimeout(() => {
        input.placeholder = hasScene
          ? 'Refine or type /brep for CAD mode\u2026'
          : 'Describe a shape\u2026';
      }, 4000);
      cleanup();
    });

    // Emit to the appropriate agent
    if (agentType === 'brep') {
      if (isRefine && lastBrepCode) {
        socket.emit('refine_brep', { instruction: promptText, code: lastBrepCode });
      } else {
        socket.emit('chat_brep', { prompt: promptText });
      }
    } else {
      if (isRefine) {
        socket.emit('refine', { instruction: promptText });
      } else {
        socket.emit('chat', { prompt: promptText });
      }
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

// Request size preview when scene updates (SDF)
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

// Request size preview for B-Rep mesh
async function fetchBrepSizePreview(code: string): Promise<void> {
  const dimensionsEl = document.getElementById('dimensions');
  try {
    // For B-Rep, we can compute dimensions from the mesh bounds
    // This is already available in the scene data
    // Just show a placeholder for now
    if (dimensionsEl) {
      dimensionsEl.textContent = 'Dimensions from mesh bounds';
      dimensionsEl.style.display = 'block';
    }
  } catch {
    // Ignore preview errors
  }
}

function openModal(el: HTMLElement | null): void {
  if (!el) return;
  (el as HTMLDialogElement).showModal();
}

function closeModal(el: HTMLElement | null): void {
  if (!el) return;
  (el as HTMLDialogElement).close();
}

function initAuthAndPrintModals(): void {
  const authBackdrop = document.getElementById('auth-modal');
  const printBackdrop = document.getElementById('print-modal');
  const authErr = document.getElementById('auth-err');
  const printErr = document.getElementById('print-err');

  const formLogin = document.getElementById('auth-form-login') as HTMLFormElement | null;
  const formReg = document.getElementById('auth-form-register') as HTMLFormElement | null;
  const tabLogin = document.getElementById('auth-tab-login');
  const tabReg = document.getElementById('auth-tab-register');

  function showAuthTab(which: 'login' | 'register'): void {
    if (formLogin && formReg) {
      formLogin.style.display = which === 'login' ? 'block' : 'none';
      formReg.style.display = which === 'register' ? 'block' : 'none';
    }
    tabLogin?.classList.toggle('active', which === 'login');
    tabReg?.classList.toggle('active', which === 'register');
    if (authErr) authErr.textContent = '';
  }

  document.getElementById('auth-open-login')?.addEventListener('click', () => {
    showAuthTab('login');
    openModal(authBackdrop);
  });
  document.getElementById('auth-open-register')?.addEventListener('click', () => {
    showAuthTab('register');
    openModal(authBackdrop);
  });
  document.getElementById('auth-cancel')?.addEventListener('click', () => closeModal(authBackdrop));
  document.getElementById('auth-cancel-2')?.addEventListener('click', () => closeModal(authBackdrop));
  tabLogin?.addEventListener('click', () => showAuthTab('login'));
  tabReg?.addEventListener('click', () => showAuthTab('register'));

  document.getElementById('auth-signout')?.addEventListener('click', () => {
    setAuthToken(null);
  });

  authBackdrop?.addEventListener('click', (e) => {
    if (e.target === authBackdrop) closeModal(authBackdrop);
  });

  formLogin?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = (document.getElementById('login-email') as HTMLInputElement).value.trim();
    const password = (document.getElementById('login-password') as HTMLInputElement).value;
    if (authErr) authErr.textContent = '';
    try {
      const r = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await parseApiJson<{ token?: string; user?: { email?: string }; error?: string }>(
        r,
        'Login',
      );
      if (!r.ok) {
        if (authErr) authErr.textContent = data.error || 'Login failed';
        return;
      }
      if (data.token) setAuthToken(data.token, data.user?.email ?? email);
      closeModal(authBackdrop);
    } catch (err) {
      if (authErr) authErr.textContent = err instanceof Error ? err.message : String(err);
    }
  });

  formReg?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = (document.getElementById('reg-email') as HTMLInputElement).value.trim();
    const password = (document.getElementById('reg-password') as HTMLInputElement).value;
    if (authErr) authErr.textContent = '';
    try {
      const r = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await parseApiJson<{ token?: string; user?: { email?: string }; error?: string }>(
        r,
        'Register',
      );
      if (!r.ok) {
        if (authErr) authErr.textContent = data.error || 'Registration failed';
        return;
      }
      if (data.token) setAuthToken(data.token, data.user?.email ?? email);
      closeModal(authBackdrop);
    } catch (err) {
      if (authErr) authErr.textContent = err instanceof Error ? err.message : String(err);
    }
  });

  const printBtn = document.getElementById('print-btn');
  printBtn?.addEventListener('click', () => {
    if (printErr) printErr.textContent = '';
    openModal(printBackdrop);
  });
  document.getElementById('print-cancel')?.addEventListener('click', () => closeModal(printBackdrop));
  printBackdrop?.addEventListener('click', (e) => {
    if (e.target === printBackdrop) closeModal(printBackdrop);
  });

  document.getElementById('print-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (printErr) printErr.textContent = '';
    const tok = getStoredToken();
    if (!tok) {
      if (printErr) printErr.textContent = 'Sign in to order a print.';
      return;
    }
    const code = lastSceneKind === 'brep' ? lastBrepCode : lastCode;
    if (!code) {
      if (printErr) printErr.textContent = 'Generate a scene first.';
      return;
    }
    const scaleMm = parseFloat((document.getElementById('print-scale') as HTMLInputElement).value);
    const material = (document.getElementById('print-material') as HTMLSelectElement).value;
    const quality = (document.getElementById('print-quality') as HTMLSelectElement).value;
    const infill = parseInt((document.getElementById('print-infill') as HTMLInputElement).value, 10);
    const colorRaw = (document.getElementById('print-color') as HTMLInputElement).value.trim();
    const delivery_speed = (document.getElementById('print-delivery') as HTMLSelectElement).value;
    const customer_name = (document.getElementById('print-name') as HTMLInputElement).value.trim();
    const shipping_address = (document.getElementById('print-address') as HTMLTextAreaElement).value.trim();

    try {
      const r = await fetch('/api/print-jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${tok}`,
        },
        body: JSON.stringify({
          geometry_kind: lastSceneKind,
          code,
          scale_mm: scaleMm,
          material,
          quality,
          infill: Number.isFinite(infill) ? infill : 20,
          color: colorRaw || null,
          customer_name,
          shipping_address,
          delivery_speed,
        }),
      });
      const data = await parseApiJson<{ error?: string; job?: { id?: string } }>(r, 'Print job');
      if (!r.ok) {
        if (printErr) printErr.textContent = data.error || `Request failed (${r.status})`;
        return;
      }
      closeModal(printBackdrop);
      const jid = data.job?.id ? ` Job #${data.job.id.slice(0, 8)}\u2026` : '';
      setStatus(`<span class="ok">Print job submitted${jid}</span>`);
    } catch (err) {
      if (printErr) printErr.textContent = err instanceof Error ? err.message : String(err);
    }
  });
}

function initExportButton(): void {
  const exportBtn = document.getElementById('export-stl') as HTMLButtonElement;

  if (!exportBtn) return;

  // Handle export click
  exportBtn.addEventListener('click', async () => {
    const code = currentAgent === 'brep' ? lastBrepCode : lastCode;
    if (!code) return;

    exportBtn.disabled = true;

    try {
      const endpoint = currentAgent === 'brep' ? '/export/stl/brep' : '/export/stl';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
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

  // Initialize both renderers
  const sdfRenderer = new WebGPURenderer();
  const brepRenderer = new BRepRenderer();

  // Track current active renderer
  let activeRenderer: 'sdf' | 'brep' = 'sdf';

  setStatus('initialising WebGPU\u2026');
  const ok = await sdfRenderer.init(canvas);
  if (!ok) {
    setStatus('<span class="err">WebGPU not supported</span>');
    initPromptBar(null, null);
    return;
  }

  // Initialize B-Rep renderer
  brepRenderer.init(canvas);

  let resizeTimer: ReturnType<typeof setTimeout>;
  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio ?? 1, 2);
    /** `clientWidth`/`clientHeight` are often 0 before first layout — no GPU draws until non-zero. */
    const cw = Math.max(
      canvas.clientWidth,
      canvas.offsetWidth,
      window.innerWidth,
      1,
    );
    const ch = Math.max(
      canvas.clientHeight,
      canvas.offsetHeight,
      window.innerHeight,
      1,
    );
    canvas.width = Math.floor(cw * dpr);
    canvas.height = Math.floor(ch * dpr);
    sdfRenderer.handleResize();
    brepRenderer.handleResize();
  };
  resize();
  requestAnimationFrame(() => {
    resize();
    requestAnimationFrame(resize);
  });
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 50);
  });
  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => resize());
    ro.observe(canvas);
  }

  sdfRenderer.setWgslScene(DEFAULT_WGSL_SCENE);
  setStatus('<span class="ok">gpu ready</span> \u00b7 connecting\u2026');

  initPromptBar(sdfRenderer, brepRenderer);

  connectAndSubscribe(
    (data) => {
      if (isWgslSdfScene(data)) {
        activeRenderer = 'sdf';
        lastSceneKind = 'wgsl-sdf';
        brepRenderer.hide();
        sdfRenderer.setWgslScene(data);
        setStatus(`<span class="ok">live</span> \u00b7 wgsl (${data.code.length} chars)`);
      } else if (isBRepMeshScene(data)) {
        activeRenderer = 'brep';
        lastSceneKind = 'brep';
        brepRenderer.show();
        brepRenderer.setMesh(data);
        const vCount = data.vertices.length;
        const fCount = data.faces.length;
        const watertight = data.is_watertight ? 'watertight' : 'not watertight';
        setStatus(`<span class="ok">live</span> \u00b7 brep (${vCount} verts, ${fCount} faces, ${watertight})`);
      } else {
        activeRenderer = 'sdf';
        brepRenderer.hide();
        sdfRenderer.setScene(data as PackedFlatIR);
        const n = (data as PackedFlatIR).instrs?.length ?? 0;
        setStatus(`<span class="ok">live</span> \u00b7 ${n} ops (flatir)`);
      }
    },
    () =>
      setStatus(
        '<span class="ok">gpu ready</span> \u00b7 <span class="ok">connected</span> \u00b7 waiting for scene\u2026',
      ),
    (err) => setStatus(`<span class="err">socket: ${err.message}</span>`),
  );

  initExportButton();
  syncAuthBar();
  initAuthAndPrintModals();

  // Render loop - render the active renderer
  const loop = () => {
    if (activeRenderer === 'brep') {
      brepRenderer.render();
    } else {
      sdfRenderer.render();
    }
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

main();