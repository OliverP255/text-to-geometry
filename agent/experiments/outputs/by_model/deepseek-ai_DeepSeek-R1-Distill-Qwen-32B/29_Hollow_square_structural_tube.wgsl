// Prompt: Hollow square structural tube: square outer profile with square inner void, long axis vertical.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdBox(p, vec3f(0.5, 1.0, 0.5));
  let inner = sdBox(p, vec3f(0.45, 1.1, 0.45));
  return opS(outer, inner);
}