// Prompt: Structural I-beam segment: vertical web with horizontal top and bottom flanges, symmetric, all from box primitives.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let web = sdBox(p, vec3f(0.05, 0.5, 0.05));
  let top_flange = sdBox(p - vec3f(0.0, 0.5, 0.0), vec3f(0.1, 0.025, 0.1));
  let bottom_flange = sdBox(p - vec3f(0.0, -0.5, 0.0), vec3f(0.1, 0.025, 0.1));
  return opU(opU(web, top_flange), bottom_flange);
}