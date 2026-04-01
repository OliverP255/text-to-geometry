// Prompt: Gear blank: Cylinder disc radius 0.28 half-height 0.045 minus central hole radius 0.09 minus offset hole radius 0.045 at (+0.11, 0, 0).
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdCylinder(p, 0.045, 0.28);
  let hole = sdCylinder(p, 0.06, 0.09);
  let q = p - vec3f(0.11, 0.0, 0.0);
  let offset_hole = sdCylinder(q, 0.06, 0.045);
  return opS(opS(outer, hole), offset_hole);
}