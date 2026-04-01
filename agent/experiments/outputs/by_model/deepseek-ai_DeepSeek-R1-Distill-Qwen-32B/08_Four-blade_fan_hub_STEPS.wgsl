// Prompt: Four-blade fan hub STEPS: 1) Hub sdCylinder r=0.095 half-h=0.055. 2) Blade sdBox (0.24, 0.018, 0.065) along +X. 3) opRotateY 90° and 180° and 270° copies union with hub—or four explicit blade boxes along ±X ±Z. 4) opU all.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let hub = sdCylinder(p, 0.055, 0.095);
  let blade_x = sdBox(p - vec3f(0.24, 0.0, 0.0), vec3f(0.24, 0.018, 0.065));
  let blade_negx = sdBox(p - vec3f(-0.24, 0.0, 0.0), vec3f(0.24, 0.018, 0.065));
  let blade_z = sdBox(p - vec3f(0.0, 0.0, 0.24), vec3f(0.24, 0.018, 0.065));
  let blade_negz = sdBox(p - vec3f(0.0, 0.0, -0.24), vec3f(0.24, 0.018, 0.065));
  let blades = opU(opU(opU(blade_x, blade_negx), blade_z), blade_negz);
  return opU(hub, blades);
}