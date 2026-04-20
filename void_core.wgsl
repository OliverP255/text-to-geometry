fn map(p: vec3f) -> f32 {
  // "Helix Form" - Twisted organic sculpture with attached spiral ribs
  // Fully 3D printable - all elements connected

  // Twist transformation - angle increases with height
  let twist = 0.6 * p.y;
  let c = cos(twist);
  let s = sin(twist);
  let q = vec3f(p.x * c + p.z * s, p.y, -p.x * s + p.z * c);

  // Main core - smooth twisted column
  let core = sdEllipsoid(q, vec3f(0.3, 1.1, 0.3));

  // Spiral rib 1 - winds around the core
  let rib1Angle = atan2(p.z, p.x);
  let rib1Height = p.y + rib1Angle * 0.35;
  let rib1Pos = vec3f(cos(rib1Angle) * 0.38, rib1Height, sin(rib1Angle) * 0.38);
  let rib1 = sdCapsule(p - rib1Pos, vec3f(0.0, -0.8, 0.0), vec3f(0.0, 0.8, 0.0), 0.08);

  // Spiral rib 2 - offset 120 degrees
  let rib2Angle = rib1Angle + 2.094;
  let rib2Height = p.y + rib2Angle * 0.35;
  let rib2Pos = vec3f(cos(rib2Angle) * 0.38, rib2Height, sin(rib2Angle) * 0.38);
  let rib2 = sdCapsule(p - rib2Pos, vec3f(0.0, -0.8, 0.0), vec3f(0.0, 0.8, 0.0), 0.08);

  // Spiral rib 3 - offset another 120 degrees
  let rib3Angle = rib1Angle + 4.189;
  let rib3Height = p.y + rib3Angle * 0.35;
  let rib3Pos = vec3f(cos(rib3Angle) * 0.38, rib3Height, sin(rib3Angle) * 0.38);
  let rib3 = sdCapsule(p - rib3Pos, vec3f(0.0, -0.8, 0.0), vec3f(0.0, 0.8, 0.0), 0.08);

  // Combine core and ribs with smooth union
  let withRibs = opSmoothUnion(opSmoothUnion(opSmoothUnion(core, rib1, 0.12), rib2, 0.12), rib3, 0.12);

  // Solid base for 3D print stability
  let base = sdCylinder(p - vec3f(0.0, -1.15, 0.0), 0.1, 0.55);

  // Top finial - elegant sphere
  let finial = sdSphere(p - vec3f(0.0, 1.2, 0.0), 0.12);

  // Combine everything
  let withBase = opSmoothUnion(withRibs, base, 0.08);
  return opSmoothUnion(withBase, finial, 0.06);
}