// Prompt: Vent cover with slots.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let base = sdBox(p, vec3f(0.5, 0.05, 0.3));
  let q = opRepPolar(p, 6.0);
  let slot = sdBox(q - vec3f(0.0, 0.25, 0.0), vec3f(0.05, 0.2, 0.15));
  return opS(base, slot);
}