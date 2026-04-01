// Prompt: Cabinet D-pull handle: horizontal grip bar with two short vertical legs down to the mounting plane.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let base = sdBox(p - vec3f(0.0, 0.25, 0.0), vec3f(0.6, 0.5, 0.15));
  let leg1 = sdCylinder(p - vec3f(0.25, 0.0, 0.0), 0.12, 0.25);
  let leg2 = sdCylinder(p - vec3f(0.35, 0.0, 0.0), 0.12, 0.25);
  return opU(base, leg1);
  return opU(base, leg2);
}