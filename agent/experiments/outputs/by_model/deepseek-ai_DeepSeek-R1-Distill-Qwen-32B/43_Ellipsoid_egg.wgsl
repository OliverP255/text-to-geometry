// Prompt: Ellipsoid egg: axis-aligned ellipsoid semi-axes 0.22, 0.32, 0.18 centered at origin—smooth closed surface.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  return sdEllipsoid(p, vec3f(0.22, 0.32, 0.18));
}