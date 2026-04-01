// Prompt: Eccentric cam STEPS: 1) Base disc sdCylinder r=0.21 half-h=0.035. 2) Boss sdCylinder r=0.095 half-h=0.055 center (+0.115, 0, 0). 3) opU.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let base = sdCylinder(p, 0.035, 0.21);
  let q = p - vec3f(0.115, 0.0, 0.0);
  let boss = sdCylinder(q, 0.055, 0.095);
  return opU(base, boss);
}