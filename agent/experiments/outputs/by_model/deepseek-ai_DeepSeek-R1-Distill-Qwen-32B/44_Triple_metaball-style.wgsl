// Prompt: Triple metaball-style: smooth union of three spheres radii 0.2, 0.18, 0.16 with centers forming a triangle in XZ at slightly different Y, k≈0.08.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let d1 = sdSphere(p - vec3f(0.5, 0.05, 0.0), 0.2);
  let d2 = sdSphere(p - vec3f(-0.25, 0.0, 0.4330), 0.18);
  let d3 = sdSphere(p - vec3f(-0.25, -0.05, -0.4330), 0.16);
  let d = opSmoothUnion(d1, d2, 0.08);
  return opSmoothUnion(d, d3, 0.08);
}