// Prompt: Flanged bearing STEPS: 1) Hollow main tube outer r=0.12 inner r=0.08 half-h=0.18. 2) Flange disc sdCylinder r=0.22 half-h=0.02 at y=-0.18. 3) opU tube and flange.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdCylinder(p, 0.18, 0.12);
  let inner = sdCylinder(p, 0.18 + 0.01, 0.08);
  let tube = opS(outer, inner);
  
  let flange = sdCylinder(p - vec3f(0.0, -0.19, 0.0), 0.02, 0.22);
  
  return opU(tube, flange);
}