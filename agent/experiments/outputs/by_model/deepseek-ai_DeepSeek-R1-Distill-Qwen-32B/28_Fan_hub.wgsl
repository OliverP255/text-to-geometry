// Prompt: Fan hub: central hub with four identical flat blades radiating along the cardinal horizontal directions, no twist.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let hub = sdCylinder(p, 0.2, 0.3);
  let q = opRepPolar(p, 4.0);
  let blade = sdRoundBox(q - vec3f(0.25, 0.0, 0.0), vec3f(0.5, 0.1, 0.05), 0.02);
  return opU(hub, blade);
}