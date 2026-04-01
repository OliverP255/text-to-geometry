// Prompt: Eccentric cam: Disc cylinder r=0.21 half-h=0.035 union boss cylinder r=0.095 half-h=0.055 at (+0.115, 0, 0).
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let disc = sdCylinder(p, 0.21, 0.035);
  let boss = sdCylinder(p - vec3f(0.115, 0.0, 0.0), 0.095, 0.055);
  return opU(disc, boss);
}