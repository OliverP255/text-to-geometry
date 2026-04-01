// Prompt: L-bracket STEPS: 1) Vertical plate sdBox half-extents (0.055, 0.16, 0.14) center (0.075, 0, 0). 2) Horizontal plate sdBox (0.13, 0.055, 0.14) center (0, -0.075, 0). 3) opU. 4) Subtract optional fillet via sdRoundBox if desired. Units: scene meters.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let vertical = sdBox(p - vec3f(0.075, 0.0, 0.0), vec3f(0.055, 0.16, 0.14));
  let horizontal = sdBox(p - vec3f(0.0, -0.075, 0.0), vec3f(0.13, 0.055, 0.14));
  let fillet = sdRoundBox(p, vec3f(0.055, 0.055, 0.14), 0.03);
  return opS(opU(vertical, horizontal), fillet);
}