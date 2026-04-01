// Prompt: Smooth blob pair: two spheres radius 0.28, centers 0.32 apart on X; combine with smooth union, blend parameter k≈0.12.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let d1 = sdSphere(p - vec3f(-0.16, 0.0, 0.0), 0.28);
  let d2 = sdSphere(p - vec3f(0.16, 0.0, 0.0), 0.28);
  return opSmoothUnion(d1, d2, 0.12);
}