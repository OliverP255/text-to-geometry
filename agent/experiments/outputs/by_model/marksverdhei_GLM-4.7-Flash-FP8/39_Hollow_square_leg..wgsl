// Prompt: Hollow square leg.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let halfSize = 0.2f;
  let thickness = 0.05f;
  let halfHeight = 0.6f;
  
  let cornerOffset = vec3f(halfSize - thickness, 0.0, halfSize - thickness);
  let innerOffset = vec3f(halfSize - thickness * 2.0, 0.0, halfSize - thickness * 2.0);
  
  let outer = sdRoundBox(p - vec3f(0.0, -halfHeight * 0.5, 0.0), vec3f(halfSize, halfHeight, halfSize), 0.02);
  let inner = sdRoundBox(p - vec3f(0.0, -halfHeight * 0.5, 0.0) + innerOffset, vec3f(halfSize - thickness * 2.0, halfHeight + 0.01, halfSize - thickness * 2.0), 0.02);
  
  return opS(outer, inner);
}