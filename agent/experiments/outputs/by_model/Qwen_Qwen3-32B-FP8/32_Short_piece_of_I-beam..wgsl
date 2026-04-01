// Prompt: Short piece of I-beam.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let flange = sdBox(p, vec3f(0.1, 0.02, 0.2));
  let web = sdBox(p - vec3f(0.0, 0.06, 0.0), vec3f(0.02, 0.12, 0.2));
  let top = opU(flange, web);
  let bottom = sdBox(p - vec3f(0.0, -0.06, 0.0), vec3f(0.1, 0.02, 0.2));
  return opU(top, bottom);
}