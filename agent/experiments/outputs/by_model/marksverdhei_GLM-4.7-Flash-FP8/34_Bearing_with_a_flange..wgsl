// Prompt: Bearing with a flange.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let flange = sdCylinder(p - vec3f(0.0, 0.26, 0.0), 0.28, 0.04);
  let outer = sdCylinder(p - vec3f(0.0, -0.26, 0.0), 0.2, 0.52);
  let inner = sdCylinder(p - vec3f(0.0, -0.26, 0.0), 0.25, 0.44);
  return opS(opU(flange, outer), inner);
}