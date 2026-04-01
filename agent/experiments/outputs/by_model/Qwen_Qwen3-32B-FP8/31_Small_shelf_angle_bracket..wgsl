// Prompt: Small shelf angle bracket.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let vert = sdBox(p - vec3f(0.0, 0.5, 0.0), vec3f(0.1, 0.5, 0.3));
  let horiz = sdBox(p - vec3f(0.35, 0.0, 0.0), vec3f(0.35, 0.1, 0.3));
  return opU(vert, horiz);
}