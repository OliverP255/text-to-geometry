// Prompt: Gear blank: Cylinder disc radius 0.28 half-height 0.045 minus central hole radius 0.09 minus offset hole radius 0.045 at (+0.11, 0, 0).
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let disc = sdCylinder(p, 0.045, 0.28);
  let centerHole = sdCylinder(p, 0.09, 0.5);
  let offsetHole = sdCylinder(p - vec3f(0.11, 0.0, 0.0), 0.045, 0.5);
  return opS(disc, opS(centerHole, offsetHole));
}