// Prompt: Fan hub: central hub with four identical flat blades radiating along the cardinal horizontal directions, no twist.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let hub = sdCylinder(p, 0.05, 0.2);
  let bladeX = sdBox(p - vec3f(0.0, 0.0, 0.12), vec3f(0.12, 0.04, 0.18));
  let bladeZ = sdBox(p - vec3f(0.0, 0.0, -0.12), vec3f(0.12, 0.04, 0.18));
  let bladeY = sdBox(p - vec3f(0.0, 0.12, 0.0), vec3f(0.12, 0.18, 0.04));
  let bladeNegY = sdBox(p - vec3f(0.0, -0.12, 0.0), vec3f(0.12, 0.18, 0.04));
  return opU(hub, opU(opU(bladeX, bladeZ), opU(bladeY, bladeNegY)));
}