// Prompt: Fan hub four blades: Hub cylinder r=0.095 half-h=0.055; four thin box blades length 0.24 width 0.065 thickness 0.036 along +X, -X, +Z, -Z; union.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let hub = sdCylinder(p, 0.055, 0.095);

  let blade1 = sdBox(p - vec3f(0.0, 0.0, 0.0), vec3f(0.12, 0.0325, 0.018));
  let blade2 = sdBox(p - vec3f(0.0, 0.0, 0.0), vec3f(0.12, 0.0325, 0.018));
  let blade3 = sdBox(p - vec3f(0.0, 0.0, 0.0), vec3f(0.018, 0.0325, 0.12));
  let blade4 = sdBox(p - vec3f(0.0, 0.0, 0.0), vec3f(0.018, 0.0325, 0.12));

  let q1 = opRotateZ(blade1, 0.0); // +X
  let q2 = opRotateZ(blade2, 3.1416); // -X
  let q3 = opRotateZ(blade3, 1.5708); // +Z
  let q4 = opRotateZ(blade4, -1.5708); // -Z

  let blades = opU(q1, opU(q2, opU(q3, q4)));
  return opU(hub, blades);
}