// Prompt: I-beam: Web box (0.04, 0.2, 0.14); top flange box (0.12, 0.025, 0.14) at y=0.225; bottom flange mirror at y=-0.225; union.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let web = sdBox(p, vec3f(0.02, 0.1, 0.07));
  let top_flange = sdBox(p - vec3f(0.0, 0.225, 0.0), vec3f(0.06, 0.0125, 0.07));
  let bottom_flange = sdBox(p - vec3f(0.0, -0.225, 0.0), vec3f(0.06, 0.0125, 0.07));
  return opU(opU(web, top_flange), bottom_flange);
}