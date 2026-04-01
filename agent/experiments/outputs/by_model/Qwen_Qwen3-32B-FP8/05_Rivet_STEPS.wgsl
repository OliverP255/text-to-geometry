// Prompt: Rivet STEPS: 1) Shank sdCylinder r=0.045 half-h=0.05 along Y. 2) Head sdSphere or sdSphere cap r=0.09 centered at (0, 0.11, 0). 3) opU.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let shank = sdCylinder(p, 0.05, 0.045);
  let head = sdSphere(p - vec3f(0.0, 0.11, 0.0), 0.09);
  return opU(shank, head);
}