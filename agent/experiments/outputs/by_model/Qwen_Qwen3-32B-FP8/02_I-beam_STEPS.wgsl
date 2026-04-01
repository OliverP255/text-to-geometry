// Prompt: I-beam STEPS: 1) Web: sdBox (0.04, 0.2, 0.14) at origin. 2) Top flange: sdBox (0.12, 0.025, 0.14) at y=+0.225. 3) Bottom flange: same at y=-0.225. 4) opU all. Symmetric in X.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let web = sdBox(p, vec3f(0.04, 0.2, 0.14));
  let flange = sdBox(p - vec3f(0.0, 0.225, 0.0), vec3f(0.12, 0.025, 0.14));
  let flange2 = sdBox(p - vec3f(0.0, -0.225, 0.0), vec3f(0.12, 0.025, 0.14));
  return opU(opU(web, flange), flange2);
}