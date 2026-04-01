// Prompt: D-pull handle: Horizontal cylinder radius 0.032, axis along X, half-length 0.16, center y=0.075; two vertical cylinders same radius half-height 0.065 at x=±0.16, y=-0.02; union.
// Model: marksverdhei/GLM-4.7-Flash-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let main = sdCylinder(p - vec3f(0.0, 0.075, 0.0), 0.16, 0.032);
  let vert1 = sdCylinder(p - vec3f(0.16, -0.02, 0.0), 0.065, 0.032);
  let vert2 = sdCylinder(p - vec3f(-0.16, -0.02, 0.0), 0.065, 0.032);
  return opU(opU(main, vert1), vert2);
}