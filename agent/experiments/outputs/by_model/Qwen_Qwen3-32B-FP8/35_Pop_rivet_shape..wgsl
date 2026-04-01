// Prompt: Pop rivet shape.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let head = sdSphere(p - vec3f(0.0, 0.08, 0.0), 0.12);
  let shaft = sdCylinder(p - vec3f(0.0, 0.11, 0.0), 0.05, 0.12);
  let hole = sdCylinder(p - vec3f(0.0, 0.24, 0.0), 0.04, 0.04);
  return opU(head, opS(shaft, hole));
}