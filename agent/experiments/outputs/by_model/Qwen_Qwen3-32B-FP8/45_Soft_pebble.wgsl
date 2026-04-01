// Prompt: Soft pebble: smooth union of sdCapsule along slight diagonal and sphere offset, k≈0.11—one continuous rounded mass.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let a = vec3f(-0.15, -0.1, 0.0);
  let b = vec3f(0.15, 0.1, 0.0);
  let capsule = sdCapsule(p, a, b, 0.12);
  let sphere = sdSphere(p - vec3f(0.0, 0.25, 0.0), 0.14);
  return opSmoothUnion(capsule, sphere, 0.11);
}