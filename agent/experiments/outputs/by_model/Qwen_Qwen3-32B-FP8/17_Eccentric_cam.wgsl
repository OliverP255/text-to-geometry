// Prompt: Eccentric cam: Disc cylinder r=0.21 half-h=0.035 union boss cylinder r=0.095 half-h=0.055 at (+0.115, 0, 0).
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let disc = sdCylinder(p, 0.035, 0.21);
  let boss = sdCylinder(p - vec3f(0.115, 0.0, 0.0), 0.055, 0.095);
  return opU(disc, boss);
}