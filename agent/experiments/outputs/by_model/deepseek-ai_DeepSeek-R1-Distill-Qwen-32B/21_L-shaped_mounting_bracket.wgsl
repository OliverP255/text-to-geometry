// Prompt: L-shaped mounting bracket: two perpendicular flat plates of uniform thickness meeting at ninety degrees, rounded outer corner, Y vertical.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let vert = sdBox(p - vec3f(0.0, 0.25, 0.0), vec3f(0.05, 0.25, 0.05));
  let horiz = sdBox(p - vec3f(0.25, 0.0, 0.0), vec3f(0.25, 0.05, 0.05));
  let corner = sdRoundBox(p - vec3f(0.25, 0.25, 0.0), vec3f(0.25, 0.25, 0.25), 0.05);
  return opS(opU(vert, horiz), corner);
}