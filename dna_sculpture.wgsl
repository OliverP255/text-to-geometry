fn map(p: vec3f) -> f32 {
  // "Void Core" - Futuristic abstract sculpture
  // A monolith with carved dimensional voids

  // Main body - stretched capsule (futuristic monolith feel)
  let body = sdCapsule(p, vec3f(0.0, -0.9, 0.0), vec3f(0.0, 0.9, 0.0), 0.45);

  // First carved void - smooth subtraction of rotated box (45°)
  let q1 = opRotateY(p, 0.785);
  let void1 = sdRoundBox(q1, vec3f(0.22, 0.22, 1.6), 0.03);

  // Second carved void - perpendicular to first
  let q2 = opRotateY(p, -0.785);
  let void2 = sdRoundBox(q2, vec3f(0.22, 0.22, 1.6), 0.03);

  // Apply smooth subtractions to body
  let carved = opSmoothSubtraction(opSmoothSubtraction(body, void1, 0.08), void2, 0.08);

  // Floating torus ring around center
  let ring = sdTorus(p - vec3f(0.0, 0.0, 0.0), vec2f(0.62, 0.03));

  // End caps - small spheres
  let capTop = sdSphere(p - vec3f(0.0, 1.0, 0.0), 0.08);
  let capBot = sdSphere(p - vec3f(0.0, -1.0, 0.0), 0.08);

  // Combine - smooth union for organic feel
  let withCaps = opSmoothUnion(carved, opU(capTop, capBot), 0.05);
  return opU(withCaps, ring);
}