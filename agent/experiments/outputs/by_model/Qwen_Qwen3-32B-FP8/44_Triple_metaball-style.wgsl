// Prompt: Triple metaball-style: smooth union of three spheres radii 0.2, 0.18, 0.16 with centers forming a triangle in XZ at slightly different Y, k≈0.08.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let a = sdSphere(p - vec3f(-0.2, 0.0, 0.0), 0.2);
  let b = sdSphere(p - vec3f(0.2, 0.1, 0.0), 0.18);
  let c = sdSphere(p - vec3f(0.0, -0.15, 0.3), 0.16);
  let ab = opSmoothUnion(a, b, 0.08);
  return opSmoothUnion(ab, c, 0.08);
}