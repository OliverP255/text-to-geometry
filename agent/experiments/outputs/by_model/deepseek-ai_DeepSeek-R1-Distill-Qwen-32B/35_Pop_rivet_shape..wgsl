// Prompt: Pop rivet shape.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let main = sdCylinder(p, 0.2, 0.1);
  let head = sdSphere(p - vec3f(0.0, 0.2, 0.0), 0.08);
  let tail = sdCylinder(p - vec3f(0.0, -0.2, 0.0), 0.2, 0.12);
  return opU(opU(main, head), tail);
}