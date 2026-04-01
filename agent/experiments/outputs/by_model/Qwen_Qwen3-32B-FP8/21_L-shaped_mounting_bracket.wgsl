// Prompt: L-shaped mounting bracket: two perpendicular flat plates of uniform thickness meeting at ninety degrees, rounded outer corner, Y vertical.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let thickness = 0.04;
  let vert = sdBox(p - vec3f(0.0, 0.5 - thickness / 2.0, 0.0), vec3f(0.1, thickness, 0.3));
  let horiz = sdBox(p - vec3f(0.35 - thickness / 2.0, 0.0, 0.0), vec3f(thickness, 0.1, 0.3));
  return opU(vert, horiz);
}