// Prompt: Hollow square structural tube: square outer profile with square inner void, long axis vertical.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdRoundBox(p - vec3f(0.0, 0.0, 0.0), vec3f(0.4, 1.6, 0.4), 0.02);
  let inner = sdRoundBox(p - vec3f(0.0, 0.0, 0.0), vec3f(0.42, 1.62, 0.42), 0.02);
  return opS(outer, inner);
}