// Prompt: Drilled gear disc.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let body = sdCylinder(p, 0.1, 0.4);
  let hole = sdCylinder(p, 0.11, 0.15);
  let q = opRepPolar(p, 8.0);
  let tooth = sdBox(q - vec3f(0.11, 0.0, 0.0), vec3f(0.04, 0.15, 0.04));
  return opS(opU(body, tooth), hole);
}