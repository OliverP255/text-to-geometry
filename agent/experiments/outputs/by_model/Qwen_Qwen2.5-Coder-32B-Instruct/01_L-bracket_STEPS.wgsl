// Prompt: L-bracket STEPS: 1) Vertical plate sdBox half-extents (0.055, 0.16, 0.14) center (0.075, 0, 0). 2) Horizontal plate sdBox (0.13, 0.055, 0.14) center (0, -0.075, 0). 3) opU. 4) Subtract optional fillet via sdRoundBox if desired. Units: scene meters.
// Model: Qwen/Qwen2.5-Coder-32B-Instruct
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let vert  = sdBox(p - vec3f(0.075, 0.0, 0.0), vec3f(0.055, 0.16, 0.14));
  let horiz = sdBox(p - vec3f(0.0, -0.075, 0.0), vec3f(0.13, 0.055, 0.14));
  let bracket = opU(vert, horiz);
  let fillet = sdRoundBox(p - vec3f(0.075, -0.075, 0.0), vec3f(0.06, 0.06, 0.14), 0.06);
  return opS(bracket, fillet);
}