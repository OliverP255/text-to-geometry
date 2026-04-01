// Prompt: Eccentric cam STEPS: 1) Base disc sdCylinder r=0.21 half-h=0.035. 2) Boss sdCylinder r=0.095 half-h=0.055 center (+0.115, 0, 0). 3) opU.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let base = sdCylinder(p, 0.21, 0.035);
  let boss = sdCylinder(p - vec3f(0.115, 0.0, 0.0), 0.095, 0.055);
  return opU(base, boss);
}