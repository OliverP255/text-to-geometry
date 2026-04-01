// Prompt: Gear blank disc: circular disc with a large central through-hole and one smaller off-center hole for a bolt pattern.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdCylinder(p - vec3f(0.0, 0.0, 0.0), 0.5, 0.06);
  let large_hole = sdCylinder(p - vec3f(0.0, 0.0, 0.0), 0.51, 0.02);
  let bolt_pattern = opRepPolar(p - vec3f(0.35, 0.0, 0.0), 6.0);
  let small_hole = sdCylinder(bolt_pattern, 0.11, 0.02);
  return opS(outer, opS(large_hole, small_hole));
}