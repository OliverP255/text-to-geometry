// Prompt: Soft pebble: smooth union of sdCapsule along slight diagonal and sphere offset, k≈0.11—one continuous rounded mass.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let d1 = sdCapsule(p, vec3f(-0.2, -0.2, 0.0), vec3f(0.2, 0.2, 0.0), 0.25);
  let d2 = sdSphere(p - vec3f(0.3, 0.1, 0.0), 0.3);
  return opSmoothUnion(d1, d2, 0.11);
}