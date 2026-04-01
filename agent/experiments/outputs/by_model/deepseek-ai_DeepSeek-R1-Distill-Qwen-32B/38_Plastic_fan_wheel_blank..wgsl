// Prompt: Plastic fan wheel blank.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let disk = sdCylinder(p, 0.05, 0.5);
  let q = opRepPolar(p, 6.0);
  let hole = sdCylinder(q - vec3f(0.45, 0.0, 0.0), 0.05, 0.06);
  return opS(disk, hole);
}