// Prompt: Four-blade fan hub STEPS: 1) Hub sdCylinder r=0.095 half-h=0.055. 2) Blade sdBox (0.24, 0.018, 0.065) along +X. 3) opRotateY 90° and 180° and 270° copies union with hub—or four explicit blade boxes along ±X ±Z. 4) opU all.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let hub = sdCylinder(p, 0.095, 0.055);
  let blade1 = sdBox(p - vec3f(0.26, 0.0, 0.0), vec3f(0.24, 0.018, 0.065));
  let blade2 = sdBox(opRotateY(p - vec3f(0.0, 0.0, 0.26), 1.5708), vec3f(0.24, 0.018, 0.065));
  let blade3 = sdBox(opRotateY(p - vec3f(-0.26, 0.0, 0.0), 3.14159), vec3f(0.24, 0.018, 0.065));
  let blade4 = sdBox(opRotateY(p - vec3f(0.0, 0.0, -0.26), 4.71239), vec3f(0.24, 0.018, 0.065));
  return opU(opU(opU(hub, blade1), blade2), opU(blade3, blade4));
}