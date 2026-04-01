// Prompt: Rivet fastener: short cylindrical shank with a hemispherical or domed head on top.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let shank = sdCylinder(p, 0.08, 0.2);
  let head = sdSphere(p, 0.08);
  return opU(shank, head);
}