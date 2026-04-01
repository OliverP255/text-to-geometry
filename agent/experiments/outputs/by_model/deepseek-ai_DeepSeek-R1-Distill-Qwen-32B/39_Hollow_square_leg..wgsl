// Prompt: Hollow square leg.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdRoundBox(p, vec3f(0.4, 0.4, 0.4), 0.05);
  let inner = sdRoundBox(p, vec3f(0.35, 0.4, 0.35), 0.03);
  return opS(outer, inner);
}