import type { PackedFlatIR } from './types';
import { FlatOp } from './types';

const WGSL = `
struct Uniforms {
  resolution: vec2f,
  cameraPos: vec3f,
  cameraDir: vec3f,
  cameraUp: vec3f,
  fov: f32,
  rootTemp: u32,
}

@group(0) @binding(0) var<uniform> u: Uniforms;
@group(0) @binding(1) var<storage, read> transforms: array<vec4f>;
@group(0) @binding(2) var<storage, read> spheres: array<vec4f>;
@group(0) @binding(3) var<storage, read> boxes: array<vec4f>;
@group(0) @binding(4) var<storage, read> planes: array<vec4f>;
@group(0) @binding(5) var<storage, read> instrs: array<vec4u>;
@group(0) @binding(6) var outImage: texture_storage_2d<rgba8unorm, write>;

const MAX_STEPS = 128u;
const MAX_DIST = 100.0;
const SURF_DIST = 0.001;

fn sdfSphere(p: vec3f, r: f32) -> f32 {
  return length(p) - r;
}

fn sdfBox(p: vec3f, b: vec3f) -> f32 {
  let q = abs(p) - b;
  return length(max(q, vec3f(0.0))) + min(max(q.x, max(q.y, q.z)), 0.0);
}

fn sdfPlane(p: vec3f, n: vec3f, d: f32) -> f32 {
  return dot(p, n) + d;
}

fn minScale(s: vec3f) -> f32 {
  return min(s.x, min(s.y, s.z));
}

fn evalSdf(rayOrigin: vec3f) -> f32 {
  var temps: array<f32, 64>;
  var tempCount = 0u;

  let numInstrs = arrayLength(&instrs);
  for (var i = 0u; i < numInstrs; i++) {
    let instr = instrs[i];
    let op = instr.x;
    let arg0 = instr.y;
    let arg1 = instr.z;
    let constIdx = instr.w;

    if (op == 0u) {
      let ti = arg0;
      let pos = transforms[ti * 2u];
      let scale = transforms[ti * 2u + 1u];
      let pLocal = (rayOrigin - pos.xyz) / scale.xyz;
      let r = spheres[constIdx].x;
      let dLocal = sdfSphere(pLocal, r);
      temps[tempCount] = dLocal * minScale(scale.xyz);
      tempCount++;
    } else if (op == 1u) {
      let ti = arg0;
      let pos = transforms[ti * 2u];
      let scale = transforms[ti * 2u + 1u];
      let pLocal = (rayOrigin - pos.xyz) / scale.xyz;
      let he = boxes[constIdx].xyz;
      let dLocal = sdfBox(pLocal, he);
      temps[tempCount] = dLocal * minScale(scale.xyz);
      tempCount++;
    } else if (op == 2u) {
      let ti = arg0;
      let pos = transforms[ti * 2u];
      let scale = transforms[ti * 2u + 1u];
      let pLocal = (rayOrigin - pos.xyz) / scale.xyz;
      let n = planes[constIdx].xyz;
      let d = planes[constIdx].w;
      let dLocal = sdfPlane(pLocal, n, d);
      temps[tempCount] = dLocal * minScale(scale.xyz);
      tempCount++;
    } else if (op == 3u) {
      let a = select(1e10, temps[arg0], arg0 < tempCount);
      let b = select(1e10, temps[arg1], arg1 < tempCount);
      temps[tempCount] = min(a, b);
      tempCount++;
    } else if (op == 4u) {
      let a = select(1e10, temps[arg0], arg0 < tempCount);
      let b = select(1e10, temps[arg1], arg1 < tempCount);
      temps[tempCount] = max(a, b);
      tempCount++;
    } else if (op == 5u) {
      let a = select(1e10, temps[arg0], arg0 < tempCount);
      let b = select(1e10, temps[arg1], arg1 < tempCount);
      temps[tempCount] = max(a, -b);
      tempCount++;
    }
  }

  let root = u.rootTemp;
  return select(1e10, temps[root], root < tempCount);
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) id: vec3u) {
  let dims = textureDimensions(outImage);
  if (id.x >= dims.x || id.y >= dims.y) { return; }

  let uv = (vec2f(f32(id.x), f32(id.y)) + 0.5) / vec2f(f32(dims.x), f32(dims.y));
  let aspect = f32(dims.x) / f32(dims.y);
  let fov = u.fov;
  let rd = normalize(u.cameraDir + (uv.x - 0.5) * aspect * tan(fov * 0.5) * vec3f(1,0,0) + (uv.y - 0.5) * tan(fov * 0.5) * vec3f(0,1,0));
  let ro = u.cameraPos;

  var d = 0.0;
  for (var i = 0u; i < MAX_STEPS; i++) {
    let p = ro + rd * d;
    let ds = evalSdf(p);
    d += ds;
    if (ds < SURF_DIST || d > MAX_DIST) { break; }
  }

  let n = 1.0 - min(d / 20.0, 1.0);
  textureStore(outImage, vec2i(i32(id.x), i32(id.y)), vec4f(n, n, n * 1.2, 1.0));
}
`;


export class WebGPURenderer {
  private device!: GPUDevice;
  private pipeline!: GPUComputePipeline;
  private bindGroup!: GPUBindGroup;
  private outputTexture!: GPUTexture;
  private canvasContext!: GPUCanvasContext;
  private canvasFormat!: GPUTextureFormat;
  private scene: PackedFlatIR | null = null;
  private camera = { pos: [0, 0, 5] as [number, number, number], dir: [0, 0, -1] as [number, number, number], up: [0, 1, 0] as [number, number, number], fov: 0.8 };

  async init(canvas: HTMLCanvasElement): Promise<boolean> {
    const adapter = await navigator.gpu?.requestAdapter();
    if (!adapter) return false;
    this.device = await adapter.requestDevice();
    if (!this.device) return false;
    this.device.addEventListener('uncapturederror', (e) => {
      console.error('[WebGPU]', e.error);
    });

    const shaderModule = this.device.createShaderModule({ code: WGSL });
    this.canvasContext = canvas.getContext('webgpu')!;
    if (!this.canvasContext) return false;

    this.canvasFormat = 'rgba8unorm';
    this.canvasContext.configure({ device: this.device, format: this.canvasFormat, alphaMode: 'opaque' });

    this.pipeline = this.device.createComputePipeline({
      layout: 'auto',
      compute: { module: shaderModule, entryPoint: 'main' },
    });
    return true;
  }

  setScene(scene: PackedFlatIR): void {
    this.scene = scene;
  }

  async render(): Promise<void> {
    if (!this.scene || !this.device) return;

    const canvas = this.canvasContext.canvas;
    const width = canvas.width;
    const height = canvas.height;
    if (width === 0 || height === 0) return;

    const { instrs, transforms, spheres, boxes, planes, rootTemp } = this.scene;

    const transformBuf = this.device.createBuffer({
      size: Math.max(transforms.length * 4, 16),
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
    });
    this.device.queue.writeBuffer(transformBuf, 0, new Float32Array(transforms));

    const sphereBuf = this.device.createBuffer({
      size: Math.max(spheres.length * 4, 16),
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
    });
    this.device.queue.writeBuffer(sphereBuf, 0, new Float32Array(spheres));

    const boxBuf = this.device.createBuffer({
      size: Math.max(boxes.length * 4, 16),
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
    });
    this.device.queue.writeBuffer(boxBuf, 0, new Float32Array(boxes));

    const planeBuf = this.device.createBuffer({
      size: Math.max(planes.length * 4, 16),
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
    });
    this.device.queue.writeBuffer(planeBuf, 0, new Float32Array(planes));

    const instrData = new Uint32Array(instrs.length * 4);
    for (let i = 0; i < instrs.length; i++) {
      instrData[i * 4] = instrs[i].op;
      instrData[i * 4 + 1] = instrs[i].arg0;
      instrData[i * 4 + 2] = instrs[i].arg1;
      instrData[i * 4 + 3] = instrs[i].constIdx;
    }
    const instrBuf = this.device.createBuffer({
      size: Math.max(instrData.byteLength, 16),
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
    });
    this.device.queue.writeBuffer(instrBuf, 0, instrData);

    const uniformData = new ArrayBuffer(80);
    const uniformF32 = new Float32Array(uniformData);
    const uniformU32 = new Uint32Array(uniformData);
    uniformF32[0] = width;
    uniformF32[1] = height;
    uniformF32[4] = this.camera.pos[0];
    uniformF32[5] = this.camera.pos[1];
    uniformF32[6] = this.camera.pos[2];
    uniformF32[8] = this.camera.dir[0];
    uniformF32[9] = this.camera.dir[1];
    uniformF32[10] = this.camera.dir[2];
    uniformF32[12] = this.camera.up[0];
    uniformF32[13] = this.camera.up[1];
    uniformF32[14] = this.camera.up[2];
    uniformF32[15] = this.camera.fov;
    uniformU32[16] = rootTemp;

    const uniformBuf = this.device.createBuffer({
      size: 80,
      usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
    });
    this.device.queue.writeBuffer(uniformBuf, 0, uniformData.slice(0, 80));

    this.outputTexture = this.device.createTexture({
      size: [width, height, 1],
      format: this.canvasFormat,
      usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.COPY_SRC,
    });

    this.bindGroup = this.device.createBindGroup({
      layout: this.pipeline.getBindGroupLayout(0),
      entries: [
        { binding: 0, resource: { buffer: uniformBuf } },
        { binding: 1, resource: { buffer: transformBuf } },
        { binding: 2, resource: { buffer: sphereBuf } },
        { binding: 3, resource: { buffer: boxBuf } },
        { binding: 4, resource: { buffer: planeBuf } },
        { binding: 5, resource: { buffer: instrBuf } },
        { binding: 6, resource: this.outputTexture.createView() },
      ],
    });

    const encoder = this.device.createCommandEncoder();
    const pass = encoder.beginComputePass();
    pass.setPipeline(this.pipeline);
    pass.setBindGroup(0, this.bindGroup);
    pass.dispatchWorkgroups(Math.ceil(width / 8), Math.ceil(height / 8));
    pass.end();

    const canvasTexture = this.canvasContext.getCurrentTexture();
    encoder.copyTextureToTexture(
      { texture: this.outputTexture },
      { texture: canvasTexture },
      [width, height, 1]
    );
    this.device.queue.submit([encoder.finish()]);

    transformBuf.destroy();
    sphereBuf.destroy();
    boxBuf.destroy();
    planeBuf.destroy();
    instrBuf.destroy();
    uniformBuf.destroy();
    this.outputTexture.destroy();
  }
}
