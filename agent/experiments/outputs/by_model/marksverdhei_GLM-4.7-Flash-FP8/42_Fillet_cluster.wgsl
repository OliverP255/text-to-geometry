// Prompt: Fillet cluster: sdRoundBox main (0.14, 0.14, 0.14) corner radius 0.03 union smooth with sphere radius 0.1 at outer +X+Y+Z corner, k≈0.1.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let rbox = sdRoundBox(p, vec3f(0.14, 0.14, 0.14), 0.03);
  let sphere_pos = p - vec3f(0.14, 0.14, 0.14);
  let sphere = sdSphere(sphere_pos, 0.1);
  return opSmoothUnion(rbox, sphere, 0.1);
}