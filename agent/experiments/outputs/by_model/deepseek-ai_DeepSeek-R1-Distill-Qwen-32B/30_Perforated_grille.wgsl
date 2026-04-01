// Prompt: Perforated grille: flat plate with a row of evenly spaced long narrow through-slots.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let plate = sdBox(p, vec3f(0.5, 0.05, 0.5));
  
  let slots = opRepPolar(p, 5.0);
  let slots = slots + vec3f(0.2, 0.0, 0.0);
  let slots = sdCylinder(slots, 0.06, 0.01);
  
  return opS(plate, slots);
}