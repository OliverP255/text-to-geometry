// Prompt: Rivet: Shank cylinder radius 0.045 half-height 0.05; head sphere radius 0.09 centered (0, 0.11, 0); union.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let shank = sdCylinder(p, 0.05, 0.045);
  let head = sdSphere(p - vec3f(0.0, 0.11, 0.0), 0.09);
  return opU(shank, head);
}