// Prompt: Perforated grille: flat plate with a row of evenly spaced long narrow through-slots.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let plate = sdBox(p, vec3f(0.5, 0.02, 1.0));
  let hole = sdBox(p - vec3f(0.0, 0.0, 0.6), vec3f(0.02, 0.04, 0.5));
  let q = opRepPolar(p, 8.0);
  let slot = sdBox(q - vec3f(0.0, 0.0, 0.6), vec3f(0.02, 0.04, 0.5));
  return opS(plate, opS(hole, slot));
}