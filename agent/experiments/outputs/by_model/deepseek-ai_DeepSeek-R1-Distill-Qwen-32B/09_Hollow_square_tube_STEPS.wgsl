// Prompt: Hollow square tube STEPS: 1) Outer sdBox (0.095, 0.26, 0.095). 2) Subtract inner sdBox (0.078, 0.27, 0.078). Y vertical.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdBox(p, vec3f(0.095, 0.26, 0.095));
  let inner = sdBox(p, vec3f(0.078, 0.27, 0.078));
  return opS(outer, inner);
}