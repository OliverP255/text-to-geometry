// Prompt: Soft pebble: smooth union of sdCapsule along slight diagonal and sphere offset, k≈0.11—one continuous rounded mass.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let capsule = sdCapsule(p, vec3f(0.0, 0.0, 0.0), vec3f(0.5, 0.5, 0.5), 0.3);
  let sphere = sdSphere(p - vec3f(0.5, 0.5, 0.5), 0.4);
  return opSmoothUnion(capsule, sphere, 0.11);
}