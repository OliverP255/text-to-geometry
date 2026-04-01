// Prompt: Gear blank STEPS: 1) Main disc sdCylinder radius 0.28 half-height 0.045. 2) Subtract central hole cylinder r=0.09. 3) Subtract second hole cylinder r=0.045 center offset (+0.11, 0, 0).
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let disc = sdCylinder(p, 0.045, 0.28);
  let centerHole = sdCylinder(p, 0.045, 0.09);
  let sideHole = sdCylinder(p - vec3f(0.11, 0.0, 0.0), 0.045, 0.045);
  let d1 = opS(disc, centerHole);
  return opS(d1, sideHole);
}