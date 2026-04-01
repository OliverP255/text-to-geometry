// Prompt: Structural I-beam segment: vertical web with horizontal top and bottom flanges, symmetric, all from box primitives.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let web = sdBox(p, vec3f(0.04, 0.5, 0.12));
  let top_flange = sdBox(p - vec3f(0.0, 0.52, 0.0), vec3f(0.1, 0.04, 0.12));
  let bottom_flange = sdBox(p - vec3f(0.0, -0.52, 0.0), vec3f(0.1, 0.04, 0.12));
  return opU(web, opU(top_flange, bottom_flange));
}