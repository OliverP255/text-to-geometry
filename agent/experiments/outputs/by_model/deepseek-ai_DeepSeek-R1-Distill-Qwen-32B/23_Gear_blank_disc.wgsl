// Prompt: Gear blank disc: circular disc with a large central through-hole and one smaller off-center hole for a bolt pattern.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let disc = sdCylinder(p, 0.1, 0.8);
  let hole1 = sdCylinder(p, 0.12, 0.4);
  let hole2 = sdCylinder(p - vec3f(0.4, 0.0, 0.0), 0.12, 0.15);
  let result = opS(opS(disc, hole1), hole2);
  return result;
}