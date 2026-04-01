// Prompt: D-pull handle STEPS: 1) Bar sdCylinder radius 0.032, half-length 0.16 along X at y=+0.075. 2) Leg cylinders r=0.032 half-h=0.065 at (±0.16, -0.02, 0). 3) opU three pieces.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let bar = sdCylinder(p - vec3f(0.0, 0.075, 0.0), 0.032, 0.16);
  let leg1 = sdCylinder(p - vec3f(0.16, -0.02, 0.0), 0.032, 0.065);
  let leg2 = sdCylinder(p - vec3f(-0.16, -0.02, 0.0), 0.032, 0.065);
  return opU(bar, opU(leg1, leg2));
}