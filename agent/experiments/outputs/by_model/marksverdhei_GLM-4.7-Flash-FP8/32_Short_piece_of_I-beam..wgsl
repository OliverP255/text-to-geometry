// Prompt: Short piece of I-beam.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let width = 0.15;
  let height = 0.6;
  let thickness = 0.08;
  
  let top = sdBox(p - vec3f(0.0, height * 0.5 - thickness * 0.5, 0.0), vec3f(width * 0.5, thickness * 0.5, width * 0.5));
  let bottom = sdBox(p - vec3f(0.0, -height * 0.5 + thickness * 0.5, 0.0), vec3f(width * 0.5, thickness * 0.5, width * 0.5));
  let web = sdBox(p, vec3f(width * 0.5, height - thickness, width * 0.5));
  
  return opU(opU(top, bottom), web);
}