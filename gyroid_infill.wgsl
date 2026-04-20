fn map(p: vec3f) -> f32 {
  // Gyroid infill pattern contained inside a cylinder with 5mm walls
  // Gyroid: triply periodic minimal surface

  // Scale for gyroid pattern (smaller = denser infill)
  let scale = 0.35;
  let sp = p * scale;

  // Gyroid SDF approximation
  // f(x,y,z) = sin(x)*cos(y) + sin(y)*cos(z) + sin(z)*cos(x)
  let gx = sin(sp.x) * cos(sp.y);
  let gy = sin(sp.y) * cos(sp.z);
  let gz = sin(sp.z) * cos(sp.x);
  let gyroid = (abs(gx + gy + gz) - 0.3) / scale;

  // Outer cylinder shell (5mm walls = 0.5 radius from surface)
  let outerRadius = 2.0;
  let innerRadius = outerRadius - 0.1; // 5mm at scale 20:1
  let outerCyl = sdCylinder(p, 1.5, outerRadius);
  let innerCyl = -sdCylinder(p, 1.5, innerRadius);

  // Wall shell: outer cylinder minus inner
  let walls = opS(outerCyl, -innerCyl);

  // Top and bottom caps with holes for gyroid visibility
  let topCap = sdCylinder(p - vec3f(0.0, 1.5, 0.0), 0.1, outerRadius);
  let botCap = sdCylinder(p - vec3f(0.0, -1.5, 0.0), 0.1, outerRadius);

  // Contain gyroid inside the inner cylinder volume
  let innerVolume = sdCylinder(p, 1.4, innerRadius - 0.02);
  let containedGyroid = opI(gyroid, innerVolume);

  // Combine: walls + caps + gyroid infill
  let withCaps = opU(walls, opU(topCap, botCap));
  return opU(withCaps, containedGyroid);
}