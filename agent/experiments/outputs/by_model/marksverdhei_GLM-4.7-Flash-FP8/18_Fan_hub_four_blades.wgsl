// Prompt: Fan hub four blades: Hub cylinder r=0.095 half-h=0.055; four thin box blades length 0.24 width 0.065 thickness 0.036 along +X, -X, +Z, -Z; union.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let hub = sdCylinder(p, 0.055, 0.095);
  let blade1 = sdBox(p - vec3f(0.12, 0.0, 0.0), vec3f(0.24, 0.036, 0.065));
  let blade2 = sdBox(p - vec3f(-0.12, 0.0, 0.0), vec3f(0.24, 0.036, 0.065));
  let blade3 = sdBox(p - vec3f(0.0, 0.0, 0.12), vec3f(0.065, 0.036, 0.24));
  let blade4 = sdBox(p - vec3f(0.0, 0.0, -0.12), vec3f(0.065, 0.036, 0.24));
  return opU(hub, opU(blade1, opU(blade2, opU(blade3, blade4))));
}