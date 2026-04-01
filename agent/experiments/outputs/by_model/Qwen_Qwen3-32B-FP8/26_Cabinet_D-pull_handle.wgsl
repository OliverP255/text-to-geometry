// Prompt: Cabinet D-pull handle: horizontal grip bar with two short vertical legs down to the mounting plane.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let grip = sdBox(p - vec3f(0.0, 0.15, 0.0), vec3f(0.4, 0.05, 0.05));
  let leg1 = sdBox(p - vec3f(-0.2, 0.05, 0.0), vec3f(0.05, 0.05, 0.05));
  let leg2 = sdBox(p - vec3f(0.2, 0.05, 0.0), vec3f(0.05, 0.05, 0.05));
  return opU(opU(grip, leg1), leg2);
}