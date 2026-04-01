// Prompt: Drawer pull.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let q = opRotateY(p - vec3f(0.0, 0.0, 0.0), 1.5708);
  let body = sdCylinder(q, 0.2, 0.4);
  let knob = sdCylinder(q - vec3f(0.0, 0.3, 0.0), 0.15, 0.05);
  let innerHole = sdCylinder(q, 0.25, 0.3);
  return opS(opS(body, knob), innerHole);
}