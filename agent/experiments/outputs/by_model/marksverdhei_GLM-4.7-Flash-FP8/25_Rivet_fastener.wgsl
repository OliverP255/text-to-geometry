// Prompt: Rivet fastener: short cylindrical shank with a hemispherical or domed head on top.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let pHead = p - vec3f(0.0, 0.4, 0.0);
  let head = sdSphere(pHead, 0.2);
  let shank = sdCylinder(p - vec3f(0.0, -0.1, 0.0), 0.2, 0.4);
  let inner = sdCylinder(p - vec3f(0.0, -0.1, 0.0), 0.25, 0.3);
  return opS(opU(head, shank), inner);
}