// Prompt: Fan hub four blades: Hub cylinder r=0.095 half-h=0.055; four thin box blades length 0.24 width 0.065 thickness 0.036 along +X, -X, +Z, -Z; union.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let hub = sdCylinder(p, 0.055, 0.095);
  let blade_x_pos = sdBox(p - vec3f(0.12, 0.0, 0.0), vec3f(0.12, 0.0325, 0.018));
  let blade_x_neg = sdBox(p - vec3f(-0.12, 0.0, 0.0), vec3f(0.12, 0.0325, 0.018));
  let blade_z_pos = sdBox(p - vec3f(0.0, 0.0, 0.12), vec3f(0.12, 0.0325, 0.018));
  let blade_z_neg = sdBox(p - vec3f(0.0, 0.0, -0.12), vec3f(0.12, 0.0325, 0.018));
  let blades = opU(opU(opU(blade_x_pos, blade_x_neg), blade_z_pos), blade_z_neg);
  return opU(hub, blades);
}