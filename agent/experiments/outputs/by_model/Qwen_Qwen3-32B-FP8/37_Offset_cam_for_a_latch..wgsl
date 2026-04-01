// Prompt: Offset cam for a latch.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let cam = sdSphere(p, 0.25);
  let offset = sdSphere(p - vec3f(0.2, 0.0, 0.0), 0.15);
  let base = sdBox(p, vec3f(0.4, 0.05, 0.25));
  let result = opU(cam, offset);
  result = opU(result, base);
  return result;
}