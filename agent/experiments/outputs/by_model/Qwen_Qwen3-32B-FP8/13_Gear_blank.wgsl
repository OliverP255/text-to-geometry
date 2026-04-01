// Prompt: Gear blank: Cylinder disc radius 0.28 half-height 0.045 minus central hole radius 0.09 minus offset hole radius 0.045 at (+0.11, 0, 0).
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let disc = sdCylinder(p, 0.045, 0.28);
  let hole = sdCylinder(p, 0.045, 0.09);
  let offsetHole = sdCylinder(p - vec3f(0.11, 0.0, 0.0), 0.045, 0.045);
  return opS(opS(disc, hole), offsetHole);
}