// Prompt: Smooth blob pair: two spheres radius 0.28, centers 0.32 apart on X; combine with smooth union, blend parameter k≈0.12.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let s1 = sdSphere(p - vec3f(-0.16, 0.0, 0.0), 0.28);
  let s2 = sdSphere(p - vec3f(0.16, 0.0, 0.0), 0.28);
  return opSmoothUnion(s1, s2, 0.12);
}