// Prompt: Fillet cluster: sdRoundBox main (0.14, 0.14, 0.14) corner radius 0.03 union smooth with sphere radius 0.1 at outer +X+Y+Z corner, k≈0.1.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let box = sdRoundBox(p, vec3f(0.14, 0.14, 0.14), 0.03);
  let q = p - vec3f(0.14, 0.14, 0.14);
  let sphere = sdSphere(q, 0.1);
  return opSmoothUnion(box, sphere, 0.1);
}