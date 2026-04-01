// Prompt: Hollow square leg.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdBox(p, vec3f(0.06, 0.45, 0.06));
  let inner = sdBox(p, vec3f(0.04, 0.47, 0.04));  // slightly larger in Z/Y to ensure hollow
  return opS(outer, inner);
}