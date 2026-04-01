// Prompt: Gear blank STEPS: 1) Main disc sdCylinder radius 0.28 half-height 0.045. 2) Subtract central hole cylinder r=0.09. 3) Subtract second hole cylinder r=0.045 center offset (+0.11, 0, 0).
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let disc = sdCylinder(p, 0.28, 0.045);
  let hole1 = sdCylinder(p, 0.09, 0.046);
  let hole2 = sdCylinder(p - vec3f(0.11, 0.0, 0.0), 0.045, 0.046);
  return opS(disc, opS(hole1, hole2));
}