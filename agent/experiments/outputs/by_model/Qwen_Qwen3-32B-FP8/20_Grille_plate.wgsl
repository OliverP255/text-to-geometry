// Prompt: Grille plate: Plate box (0.26, 0.032, 0.18); eight slot boxes half-extents (0.012, 0.04, 0.19) at x = -0.105 + i*0.03 for i=0..7; subtract all from plate.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let plate = sdBox(p, vec3f(0.26, 0.032, 0.18));

  let slot = sdBox(p, vec3f(0.012, 0.04, 0.19));
  let slots = opRepPolar(p, 8.0);
  let slotTrans = sdBox(slots - vec3f(-0.105, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));

  return opS(plate, slotTrans);
}