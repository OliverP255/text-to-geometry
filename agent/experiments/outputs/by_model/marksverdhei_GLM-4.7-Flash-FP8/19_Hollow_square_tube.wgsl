// Prompt: Hollow square tube: Outer box half-extents (0.095, 0.26, 0.095) minus inner (0.078, 0.27, 0.078).
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let outer = sdRoundBox(p, vec3f(0.095, 0.26, 0.095), 0.0);
  let inner = sdRoundBox(p, vec3f(0.078, 0.27, 0.078), 0.0);
  return opS(outer, inner);
}