// Prompt: Flanged bearing housing: short hollow shaft with a wider flat flange on one end, axis vertical.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let shaft = sdCylinder(p, 0.12, 0.3);
  let flangePos = p - vec3f(0.0, 0.31, 0.0);
  let flange = sdRoundBox(flangePos, vec3f(0.6, 0.1, 0.6), 0.1);
  let inner = sdCylinder(p, 0.14, 0.35);
  let hole = sdRoundBox(p - vec3f(0.0, 0.25, 0.0), vec3f(0.2, 0.2, 0.2), 0.02);
  return opS(opU(flange, shaft), opI(inner, hole));
}