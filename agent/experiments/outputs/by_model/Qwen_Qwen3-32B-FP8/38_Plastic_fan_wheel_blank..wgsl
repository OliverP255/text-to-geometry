// Prompt: Plastic fan wheel blank.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let blade = sdBox(p, vec3f(0.08, 0.1, 0.15));
  let q = opRepPolar(p, 6.0);
  let blades = sdBox(q - vec3f(0.0, 0.0, 0.0), vec3f(0.08, 0.1, 0.15));
  let body = sdCylinder(p, 0.04, 0.25);
  return opU(body, blades);
}