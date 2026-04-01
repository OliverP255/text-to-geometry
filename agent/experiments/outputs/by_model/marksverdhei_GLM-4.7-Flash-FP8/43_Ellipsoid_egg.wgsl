// Prompt: Ellipsoid egg: axis-aligned ellipsoid semi-axes 0.22, 0.32, 0.18 centered at origin—smooth closed surface.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let d = sdEllipsoid(p, vec3f(0.22, 0.32, 0.18));
  return d;
}