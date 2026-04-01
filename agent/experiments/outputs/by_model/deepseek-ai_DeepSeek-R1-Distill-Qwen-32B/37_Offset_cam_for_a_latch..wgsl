// Prompt: Offset cam for a latch.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let main = sdCylinder(p, 0.1, 0.5);
  let offset = sdCylinder(opRotateX(p - vec3f(0.0, 0.5, 0.0), 1.5708), 0.25, 0.2);
  let bearing = sdCylinder(p - vec3f(0.0, -0.05, 0.0), 0.55, 0.05);
  return opSmoothUnion(main, offset, 0.05);
}