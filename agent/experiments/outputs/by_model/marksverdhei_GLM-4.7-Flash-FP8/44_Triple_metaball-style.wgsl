// Prompt: Triple metaball-style: smooth union of three spheres radii 0.2, 0.18, 0.16 with centers forming a triangle in XZ at slightly different Y, k≈0.08.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let s1 = sdSphere(p - vec3f(-0.08, -0.08, -0.08), 0.2);
  let s2 = sdSphere(p - vec3f( 0.16,  0.08, -0.08), 0.18);
  let s3 = sdSphere(p - vec3f( 0.08,  0.16,  0.16), 0.16);
  let u1 = opSmoothUnion(s1, s2, 0.08);
  return opSmoothUnion(u1, s3, 0.08);
}