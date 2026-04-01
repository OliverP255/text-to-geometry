// Prompt: Small shelf angle bracket.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let leg1 = sdBox(p - vec3f(0.0, 0.15, 0.0), vec3f(0.1, 0.3, 0.05));
  let leg2 = sdBox(p - vec3f(0.25, 0.0, 0.0), vec3f(0.3, 0.1, 0.05));
  return opU(leg1, leg2);
}