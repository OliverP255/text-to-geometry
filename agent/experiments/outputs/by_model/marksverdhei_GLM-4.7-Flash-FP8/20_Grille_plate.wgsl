// Prompt: Grille plate: Plate box (0.26, 0.032, 0.18); eight slot boxes half-extents (0.012, 0.04, 0.19) at x = -0.105 + i*0.03 for i=0..7; subtract all from plate.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let plate = sdBox(p, vec3f(0.26, 0.032, 0.18));
  let slot1 = sdBox(p - vec3f(-0.105, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let slot2 = sdBox(p - vec3f(-0.075, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let slot3 = sdBox(p - vec3f(-0.045, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let slot4 = sdBox(p - vec3f(-0.015, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let slot5 = sdBox(p - vec3f(0.015, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let slot6 = sdBox(p - vec3f(0.045, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let slot7 = sdBox(p - vec3f(0.075, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let slot8 = sdBox(p - vec3f(0.105, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  return opS(plate, opS(slot1, opS(slot2, opS(slot3, opS(slot4, opS(slot5, opS(slot6, opS(slot7, slot8))))))));
}