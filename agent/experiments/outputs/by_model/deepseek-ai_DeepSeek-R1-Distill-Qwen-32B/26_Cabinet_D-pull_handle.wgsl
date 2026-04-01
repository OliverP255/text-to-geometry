// Prompt: Cabinet D-pull handle: horizontal grip bar with two short vertical legs down to the mounting plane.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let grip = sdCylinder(p, 0.5, 0.1);
  let leg1 = sdCylinder(p - vec3f(0.0, -0.25, 0.0), 0.25, 0.05);
  let leg2 = sdCylinder(p - vec3f(0.0, -0.25, 0.0), 0.25, 0.05);
  let base = sdBox(p - vec3f(0.0, -0.5, 0.0), vec3f(0.2, 0.01, 0.2));
  return opU(grip, opU(leg1, base));
}