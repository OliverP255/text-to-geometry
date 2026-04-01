// Prompt: Vent cover with slots.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let base = sdRoundBox(p, vec3f(0.5, 0.1, 0.4), 0.05);
  let offset = opRepPolar(p, 4.0);
  let slot = sdBox(offset - vec3f(0.0, 0.0, 0.25), vec3f(0.02, 0.1, 0.05));
  let inner = sdRoundBox(p - vec3f(0.0, 0.0, 0.0), vec3f(0.4, 0.05, 0.3), 0.02);
  return opS(base, opS(inner, slot));
}