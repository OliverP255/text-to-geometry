// Prompt: Gear blank STEPS: 1) Main disc sdCylinder radius 0.28 half-height 0.045. 2) Subtract central hole cylinder r=0.09. 3) Subtract second hole cylinder r=0.045 center offset (+0.11, 0, 0).
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let disc = sdCylinder(p, 0.045, 0.28);
  let hole1 = sdCylinder(p, 0.05, 0.09);
  let hole2 = sdCylinder(p - vec3f(0.11, 0.0, 0.0), 0.05, 0.045);
  return opS(opS(disc, hole1), hole2);
}