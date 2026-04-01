// Prompt: Drilled gear disc.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let gear_radius = 0.5;
  let gear_thickness = 0.08;
  let hole_radius = 0.2;
  let hole_depth = 0.1;
  let num_holes = 12.0;

  let gear = sdCylinder(p, gear_thickness, gear_radius);
  let hole = sdCylinder(p - vec3f(0.0, 0.0, 0.0), hole_depth, hole_radius);

  let q = opRepPolar(p, num_holes);
  let hole_pattern = sdCylinder(q - vec3f(0.45, 0.0, 0.0), hole_depth, 0.02);

  let body = opS(gear, hole);
  let holes = opRepPolar(hole_pattern, num_holes);

  return opS(body, holes);
}