// Prompt: Eccentric cam plate: circular base with a second thicker circular boss offset from the rotation center.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let base = sdCylinder(p - vec3f(0.0, -0.05, 0.0), 0.1, 0.1);
  let boss = sdCylinder(p - vec3f(0.08, 0.0, 0.0), 0.05, 0.15);
  return opU(base, boss);
}