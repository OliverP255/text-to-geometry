// Prompt: Fan hub: central hub with four identical flat blades radiating along the cardinal horizontal directions, no twist.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let q = opRepPolar(p, 4.0);
  let blade = sdBox(q - vec3f(0.0, 0.0, 0.0), vec3f(0.08, 0.3, 0.05));
  let hub = sdSphere(p, 0.15);
  return opU(hub, blade);
}