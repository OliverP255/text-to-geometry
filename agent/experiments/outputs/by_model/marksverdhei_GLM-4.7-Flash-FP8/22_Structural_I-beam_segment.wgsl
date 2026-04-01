// Prompt: Structural I-beam segment: vertical web with horizontal top and bottom flanges, symmetric, all from box primitives.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let flangeW = 0.4;
  let flangeT = 0.1;
  let webH = 0.8;
  let webW = 0.1;
  let overlap = 0.01;
  let topFlange = sdBox(p - vec3f(0.0, webH * 0.5 + flangeT * 0.5 + overlap, 0.0), vec3f(flangeW, flangeT, 0.3));
  let botFlange = sdBox(p - vec3f(0.0, -webH * 0.5 - flangeT * 0.5 - overlap, 0.0), vec3f(flangeW, flangeT, 0.3));
  let web = sdBox(p - vec3f(0.0, 0.0, 0.0), vec3f(webW, webH, 0.3));
  return opU(opU(topFlange, botFlange), web);
}