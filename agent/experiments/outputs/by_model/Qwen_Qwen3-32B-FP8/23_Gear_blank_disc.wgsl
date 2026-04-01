// Prompt: Gear blank disc: circular disc with a large central through-hole and one smaller off-center hole for a bolt pattern.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let disc = sdCylinder(p, 0.1, 0.5);
  let hole = sdCylinder(p, 0.06, 0.06);  // central hole
  let boltHole = sdCylinder(p - vec3f(0.25, 0.0, 0.0), 0.03, 0.03);  // off-center bolt hole
  return opS(opS(disc, hole), boltHole);
}