// Prompt: Rivet fastener: short cylindrical shank with a hemispherical or domed head on top.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let shank = sdCylinder(p, 0.2, 0.08);  // Cylinder half-height and radius
  let head = sdSphere(p - vec3f(0.0, 0.2, 0.0), 0.1);  // Hemisphere radius and position
  let body = opU(shank, head);  // Combine shank and head
  
  // Hollow out the rivet
  let inner Shank = sdCylinder(p, 0.22, 0.07);
  let inner Head = sdSphere(p - vec3f(0.0, 0.2, 0.0), 0.09);
  let inner = opU(inner Shank, inner Head);
  
  return opS(body, inner);
}