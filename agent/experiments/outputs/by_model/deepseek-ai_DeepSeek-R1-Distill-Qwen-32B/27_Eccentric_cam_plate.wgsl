// Prompt: Eccentric cam plate: circular base with a second thicker circular boss offset from the rotation center.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let base = sdCylinder(p, 0.5, 0.5);
  let boss = sdCylinder(p - vec3f(0.4, 0.0, 0.0), 0.8, 0.35);
  return opU(base, boss);
}