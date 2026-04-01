// Prompt: L-bracket: Vertical plate half-extents (0.055, 0.16, 0.14) centered (0.075, 0, 0); horizontal plate (0.13, 0.055, 0.14) at (0, -0.075, 0); union; Y up.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let vert = sdBox(p - vec3f(0.075, 0.0, 0.0), vec3f(0.055, 0.16, 0.14));
  let horiz = sdBox(p - vec3f(0.0, -0.075, 0.0), vec3f(0.13, 0.055, 0.14));
  return opU(vert, horiz);
}