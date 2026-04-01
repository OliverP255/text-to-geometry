// Prompt: Bearing with a flange.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let body = sdCylinder(p, 0.5, 0.4);
  let flange = sdCylinder(p - vec3f(0.0, 0.5, 0.0), 0.05, 0.6);
  return opU(body, flange);
}