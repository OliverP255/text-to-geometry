// Prompt: Eccentric cam plate: circular base with a second thicker circular boss offset from the rotation center.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let base = sdCylinder(p, 0.1, 0.05);
  let boss = sdCylinder(p - vec3f(0.1, 0.0, 0.0), 0.05, 0.1);
  return opU(base, boss);
}