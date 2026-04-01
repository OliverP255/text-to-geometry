// Prompt: D-pull handle: Horizontal cylinder radius 0.032, axis along X, half-length 0.16, center y=0.075; two vertical cylinders same radius half-height 0.065 at x=±0.16, y=-0.02; union.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let center = p - vec3f(0.0, 0.075, 0.0);
  let handle = sdCylinder(center, 0.16, 0.032);

  let left = p - vec3f(-0.16, -0.02, 0.0);
  let left_post = sdCylinder(left, 0.065, 0.032);

  let right = p - vec3f(0.16, -0.02, 0.0);
  let right_post = sdCylinder(right, 0.065, 0.032);

  return opU(handle, opU(left_post, right_post));
}