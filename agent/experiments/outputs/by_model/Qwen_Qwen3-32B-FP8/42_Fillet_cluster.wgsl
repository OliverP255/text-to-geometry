// Prompt: Fillet cluster: sdRoundBox main (0.14, 0.14, 0.14) corner radius 0.03 union smooth with sphere radius 0.1 at outer +X+Y+Z corner, k≈0.1.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let main = sdRoundBox(p, vec3f(0.14, 0.14, 0.14), 0.03);
  let sphere = sdSphere(p - vec3f(0.14, 0.14, 0.14), 0.1);
  return opSmoothUnion(main, sphere, 0.1);
}