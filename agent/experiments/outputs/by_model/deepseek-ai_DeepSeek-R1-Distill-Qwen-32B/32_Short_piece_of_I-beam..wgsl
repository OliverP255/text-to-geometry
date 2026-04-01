// Prompt: Short piece of I-beam.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let web = sdBox(p, vec3f(0.02, 0.5, 0.02));
  let flange1 = sdBox(p - vec3f(0.0, 0.25, 0.0), vec3f(0.05, 0.5, 0.02));
  let flange2 = sdBox(p - vec3f(0.0, -0.25, 0.0), vec3f(0.05, 0.5, 0.02));
  return opU(web, opU(flange1, flange2));
}