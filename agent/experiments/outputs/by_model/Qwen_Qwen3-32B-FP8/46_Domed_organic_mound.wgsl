// Prompt: Domed organic mound: sdSphere radius 0.45 center (0, 0.12, 0) union smooth with wider sdCylinder pedestal radius 0.35 half-height 0.08, k≈0.14.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let q1 = p - vec3f(0.0, 0.12, 0.0);
  let sphere = sdSphere(q1, 0.45);
  let cylinder = sdCylinder(p, 0.08, 0.35);
  return opSmoothUnion(sphere, cylinder, 0.14);
}