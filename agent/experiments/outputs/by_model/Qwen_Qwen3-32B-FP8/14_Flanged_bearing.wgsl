// Prompt: Flanged bearing: Hollow cylinder outer 0.12 inner 0.08 half-height 0.18; union flange cylinder radius 0.22 half-height 0.02 with center at y=-0.18.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdCylinder(p, 0.18, 0.12);
  let inner = sdCylinder(p, 0.18, 0.08);
  let bearing = opS(outer, inner);
  let flange = sdCylinder(p - vec3f(0.0, -0.18, 0.0), 0.02, 0.22);
  return opU(bearing, flange);
}