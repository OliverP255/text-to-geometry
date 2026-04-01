// Prompt: L-shaped mounting bracket: two perpendicular flat plates of uniform thickness meeting at ninety degrees, rounded outer corner, Y vertical.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let vert = sdBox(p - vec3f(0.0, 0.25, 0.0), vec3f(0.15, 0.5, 0.05));
  let horiz = sdRoundBox(p - vec3f(0.3, 0.0, 0.0), vec3f(0.3, 0.15, 0.05), 0.015);
  return opU(vert, horiz);
}