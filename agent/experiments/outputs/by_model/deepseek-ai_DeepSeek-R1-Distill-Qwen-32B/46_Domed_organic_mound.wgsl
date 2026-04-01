// Prompt: Domed organic mound: sdSphere radius 0.45 center (0, 0.12, 0) union smooth with wider sdCylinder pedestal radius 0.35 half-height 0.08, k≈0.14.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let sphere = sdSphere(p - vec3f(0.0, 0.12, 0.0), 0.45);
  let pedestal = sdCylinder(p, 0.08, 0.35);
  return opSmoothUnion(sphere, pedestal, 0.14);
}