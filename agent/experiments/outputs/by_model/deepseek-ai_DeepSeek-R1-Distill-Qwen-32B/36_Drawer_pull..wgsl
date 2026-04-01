// Prompt: Drawer pull.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let body = sdRoundBox(p, vec3f(0.25, 0.1, 0.05), 0.03);
  let handle = sdCylinder(p - vec3f(0.0, 0.0, 0.15), 0.1, 0.05);
  let knob1 = sdSphere(p - vec3f(0.0, 0.0, 0.25), 0.03);
  let knob2 = sdSphere(p - vec3f(0.0, 0.0, 0.05), 0.03);
  return opU(opU(opU(body, handle), knob1), knob2);
}