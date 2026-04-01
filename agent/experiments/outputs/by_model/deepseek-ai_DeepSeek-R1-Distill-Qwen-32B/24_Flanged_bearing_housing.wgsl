// Prompt: Flanged bearing housing: short hollow shaft with a wider flat flange on one end, axis vertical.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let shaft_outer = sdCylinder(p, 0.5, 0.4);
  let shaft_inner = sdCylinder(p, 0.6, 0.3);
  let flange = sdRoundBox(p - vec3f(0.0, 0.5, 0.0), vec3f(0.6, 0.05, 0.6), 0.1);
  let combined = opU(shaft_outer, flange);
  return opS(combined, shaft_inner);
}