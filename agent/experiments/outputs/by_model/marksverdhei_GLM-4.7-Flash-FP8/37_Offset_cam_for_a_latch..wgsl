// Prompt: Offset cam for a latch.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let base = sdCylinder(p, 0.5, 0.2);
  let shaft = sdCylinder(p - vec3f(0.0, 0.31, 0.0), 0.35, 0.15);
  let camRot = opRotateY(p - vec3f(0.0, 0.0, 0.0), 1.5708);
  let camProfile = sdBox(camRot, vec3f(0.1, 0.2, 0.4));
  let camBody = sdRoundBox(camRot - vec3f(0.25, 0.0, 0.0), vec3f(0.15, 0.3, 0.1), 0.05);
  let cam = opU(camProfile, camBody);
  let hole = sdCylinder(p, 0.11, 0.1);
  return opS(opU(opU(base, shaft), cam), hole);
}