// Prompt: Pop rivet shape.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let head = sdRoundBox(p - vec3f(0.0, 0.22, 0.0), vec3f(0.18, 0.04, 0.18), 0.04);
  let shaft = sdCylinder(p - vec3f(0.0, 0.0, 0.0), 0.24, 0.075);
  let hole = sdCylinder(p, 0.085, 0.25);
  let innerShaft = sdCylinder(p, 0.095, 0.35);
  return opS(head, opS(opU(shaft, hole), innerShaft));
}