fn map(p: vec3f) -> f32 {
  // Gyroid infill pattern contained inside a cylinder with 5mm walls
  // Open top and bottom to see the internal gyroid structure

  // Scale for gyroid pattern (smaller = denser infill)
  let scale = 0.35;
  let sp = p * scale;

  // Gyroid SDF approximation
  // f(x,y,z) = sin(x)*cos(y) + sin(y)*cos(z) + sin(z)*cos(x)
  let gx = sin(sp.x) * cos(sp.y);
  let gy = sin(sp.y) * cos(sp.z);
  let gz = sin(sp.z) * cos(sp.x);
  let gyroid = (abs(gx + gy + gz) - 0.3) / scale;

  // Outer cylinder shell (5mm walls)
  let outerRadius = 2.0;
  let innerRadius = outerRadius - 0.1; // 5mm wall thickness
  let height = 1.5;

  // Outer cylinder
  let outerCyl = sdCylinder(p, height, outerRadius);
  // Inner cylinder (to subtract)
  let innerCyl = sdCylinder(p, height - 0.05, innerRadius);

  // Wall shell: outer minus inner (open top/bottom)
  let walls = opS(outerCyl, innerCyl);

  // Contain gyroid inside the inner cylinder volume
  let innerVolume = sdCylinder(p, height - 0.1, innerRadius - 0.02);
  let containedGyroid = opI(gyroid, innerVolume);

  // Combine: walls + gyroid infill
  return opU(walls, containedGyroid);
}