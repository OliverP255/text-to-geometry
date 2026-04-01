// Prompt: Drawer pull.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let handle = sdCylinder(p, 0.1, 0.4);
  let cap = sdSphere(p, 0.12);
  let d1 = opU(handle, cap - vec3f(0.0, 0.4, 0.0));
  let d2 = sdSphere(p - vec3f(0.0, 0.0, 0.4), 0.05);
  return opU(d1, d2);
}