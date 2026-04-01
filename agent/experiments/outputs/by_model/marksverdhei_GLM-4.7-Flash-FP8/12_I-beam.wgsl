// Prompt: I-beam: Web box (0.04, 0.2, 0.14); top flange box (0.12, 0.025, 0.14) at y=0.225; bottom flange mirror at y=-0.225; union.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let web = sdBox(p - vec3f(0.0, 0.0, 0.0), vec3f(0.04, 0.2, 0.14));
  let top = sdBox(p - vec3f(0.0, 0.225, 0.0), vec3f(0.12, 0.025, 0.14));
  let bot = sdBox(p - vec3f(0.0, -0.225, 0.0), vec3f(0.12, 0.025, 0.14));
  return opU(web, opU(top, bot));
}