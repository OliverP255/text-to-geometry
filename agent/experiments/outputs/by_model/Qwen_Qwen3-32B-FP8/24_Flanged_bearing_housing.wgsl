// Prompt: Flanged bearing housing: short hollow shaft with a wider flat flange on one end, axis vertical.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let shaft = sdCylinder(p - vec3f(0.0, 0.05, 0.0), 0.25, 0.15);
  let innerShaft = sdCylinder(p - vec3f(0.0, 0.05, 0.0), 0.26, 0.14);
  let flange = sdBox(p - vec3f(0.0, 0.26, 0.0), vec3f(0.4, 0.04, 0.2));
  let innerFlange = sdBox(p - vec3f(0.0, 0.26, 0.0), vec3f(0.35, 0.03, 0.15));
  let outerFlange = sdBox(p - vec3f(0.0, 0.26, 0.0), vec3f(0.45, 0.05, 0.25));
  let shaftHollow = opS(shaft, innerShaft);
  let flangeHollow = opS(outerFlange, innerFlange);
  return opU(shaftHollow, flangeHollow);
}