// Prompt: Four-blade fan hub STEPS: 1) Hub sdCylinder r=0.095 half-h=0.055. 2) Blade sdBox (0.24, 0.018, 0.065) along +X. 3) opRotateY 90° and 180° and 270° copies union with hub—or four explicit blade boxes along ±X ±Z. 4) opU all.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let hub = sdCylinder(p, 0.055, 0.095);

  let blade0 = sdBox(p - vec3f(0.12, 0.0, 0.0), vec3f(0.24, 0.018, 0.065));
  let blade1 = sdBox(opRotateY(p, 1.5708) - vec3f(0.12, 0.0, 0.0), vec3f(0.24, 0.018, 0.065));
  let blade2 = sdBox(opRotateY(p, 3.1416) - vec3f(0.12, 0.0, 0.0), vec3f(0.24, 0.018, 0.065));
  let blade3 = sdBox(opRotateY(p, 4.7124) - vec3f(0.12, 0.0, 0.0), vec3f(0.24, 0.018, 0.065));

  return opU(hub, opU(blade0, opU(blade1, opU(blade2, blade3))));
}