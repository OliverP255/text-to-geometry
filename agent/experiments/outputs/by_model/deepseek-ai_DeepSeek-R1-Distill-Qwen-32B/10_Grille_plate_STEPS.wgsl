// Prompt: Grille plate STEPS: 1) Plate sdBox (0.26, 0.032, 0.18). 2) For i=0..7 subtract slot sdBox (0.012, 0.04, 0.19) center at (-0.105 + i*0.03, 0, 0). Eight slots.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let plate = sdBox(p, vec3f(0.26, 0.032, 0.18));
  let slot = sdBox(p - vec3f(-0.105, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let slots = opRepPolar(slot, 8.0);
  return opS(plate, slots);
}