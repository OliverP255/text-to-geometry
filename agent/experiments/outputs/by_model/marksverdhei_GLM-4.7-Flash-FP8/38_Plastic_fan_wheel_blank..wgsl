// Prompt: Plastic fan wheel blank.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let hub = sdCylinder(p, 0.08, 0.3);
  let blade = sdBox(p - vec3f(0.15, 0.0, 0.0), vec3f(0.35, 0.02, 0.12));
  let q = opRepPolar(p, 5.0);
  let blades = sdBox(q - vec3f(0.15, 0.0, 0.0), vec3f(0.35, 0.02, 0.12));
  let result = opU(blades, hub);
  return result;
}