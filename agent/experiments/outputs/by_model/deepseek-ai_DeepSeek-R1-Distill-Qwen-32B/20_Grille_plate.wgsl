// Prompt: Grille plate: Plate box (0.26, 0.032, 0.18); eight slot boxes half-extents (0.012, 0.04, 0.19) at x = -0.105 + i*0.03 for i=0..7; subtract all from plate.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let plate = sdBox(p, vec3f(0.26, 0.032, 0.18));
  let slot = sdBox(p, vec3f(0.012, 0.04, 0.19));
  
  let s0 = sdBox(p - vec3f(-0.105, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s1 = sdBox(p - vec3f(-0.075, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s2 = sdBox(p - vec3f(-0.045, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s3 = sdBox(p - vec3f(-0.015, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s4 = sdBox(p - vec3f(0.015, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s5 = sdBox(p - vec3f(0.045, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s6 = sdBox(p - vec3f(0.075, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s7 = sdBox(p - vec3f(0.105, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  
  let slots = opU(opU(opU(opU(opU(opU(opU(s0, s1), s2), s3), s4), s5), s6), s7);
  
  return opS(plate, slots);
}