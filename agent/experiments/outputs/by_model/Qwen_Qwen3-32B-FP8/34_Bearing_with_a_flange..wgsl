// Prompt: Bearing with a flange.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let bearing = sdCylinder(p, 0.1, 0.45);
  let inner = sdCylinder(p, 0.1, 0.55);
  let outer = sdCylinder(p, 0.25, 0.55);
  let bearingShell = opS(outer, inner);
  let flange = sdBox(p - vec3f(0.0, 0.46, 0.0), vec3f(0.3, 0.1, 0.3));
  let flangeHole = sdCylinder(p - vec3f(0.0, 0.46, 0.0), 0.1, 0.1);
  let flangeShell = opS(flange, flangeHole);
  return opU(bearingShell, flangeShell);
}