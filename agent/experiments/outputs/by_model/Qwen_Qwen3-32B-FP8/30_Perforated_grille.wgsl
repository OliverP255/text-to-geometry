// Prompt: Perforated grille: flat plate with a row of evenly spaced long narrow through-slots.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let plate = sdBox(p, vec3f(0.1, 0.02, 0.5));
  
  let slot = sdBox(p, vec3f(0.02, 0.04, 0.5));
  let q = opRepPolar(p, 5.0); // 5 slots
  let slots = sdBox(q - vec3f(0.0, 0.0, 0.0), vec3f(0.02, 0.04, 0.5));
  
  return opS(plate, slots);
}