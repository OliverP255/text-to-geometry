// Prompt: Small shelf angle bracket.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let vert = sdBox(p - vec3f(0.0, 0.25, 0.0), vec3f(0.05, 0.25, 0.05));
  let horiz = sdBox(p - vec3f(0.175, 0.0, 0.0), vec3f(0.175, 0.05, 0.05));
  return opU(vert, horiz);
}