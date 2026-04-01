// Prompt: Hollow square structural tube: square outer profile with square inner void, long axis vertical.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdBox(p, vec3f(0.5, 0.26, 0.5));
  let inner = sdBox(p, vec3f(0.48, 0.28, 0.48)); // slightly larger in Y
  return opS(outer, inner);
}