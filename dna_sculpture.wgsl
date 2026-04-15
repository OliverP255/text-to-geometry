fn map(p: vec3f) -> f32 {
  // DNA-inspired sculpture - double helix with base pairs
  // All elements connected for 3D printability

  // Noise for organic surface detail
  let n = fract(sin(dot(p, vec3f(12.9898, 78.233, 45.164))) * 43758.5453);

  // === DOUBLE HELIX BACKBONES ===
  // Two intertwined spiral strands
  let helixRadius = 0.35;
  let helixPitch = 1.2; // Vertical rise per revolution

  // Strand 1 - ascending spiral backbone
  let angle1 = p.y * 3.14159 * 2.0 / helixPitch;
  let strand1Pos = vec3f(cos(angle1) * helixRadius, 0.0, sin(angle1) * helixRadius);
  let strand1 = sdCylinder(p - strand1Pos, 2.0, 0.06); // Full height cylinder

  // Strand 2 - offset by 180 degrees
  let angle2 = angle1 + 3.14159;
  let strand2Pos = vec3f(cos(angle2) * helixRadius, 0.0, sin(angle2) * helixRadius);
  let strand2 = sdCylinder(p - strand2Pos, 2.0, 0.06);

  // === BASE PAIRS - Connecting rungs ===
  // Ladder-like connections between strands
  // 12 base pairs along the height
  let bp1 = sdCapsule(p, vec3f(cos(0.0) * helixRadius, -1.8, sin(0.0) * helixRadius), vec3f(cos(3.14159) * helixRadius, -1.8, sin(3.14159) * helixRadius), 0.025);

  let bp2 = sdCapsule(p, vec3f(cos(0.524) * helixRadius, -1.5, sin(0.524) * helixRadius), vec3f(cos(0.524 + 3.14159) * helixRadius, -1.5, sin(0.524 + 3.14159) * helixRadius), 0.025);

  let bp3 = sdCapsule(p, vec3f(cos(1.047) * helixRadius, -1.2, sin(1.047) * helixRadius), vec3f(cos(1.047 + 3.14159) * helixRadius, -1.2, sin(1.047 + 3.14159) * helixRadius), 0.025);

  let bp4 = sdCapsule(p, vec3f(cos(1.571) * helixRadius, -0.9, sin(1.571) * helixRadius), vec3f(cos(1.571 + 3.14159) * helixRadius, -0.9, sin(1.571 + 3.14159) * helixRadius), 0.025);

  let bp5 = sdCapsule(p, vec3f(cos(2.094) * helixRadius, -0.6, sin(2.094) * helixRadius), vec3f(cos(2.094 + 3.14159) * helixRadius, -0.6, sin(2.094 + 3.14159) * helixRadius), 0.025);

  let bp6 = sdCapsule(p, vec3f(cos(2.618) * helixRadius, -0.3, sin(2.618) * helixRadius), vec3f(cos(2.618 + 3.14159) * helixRadius, -0.3, sin(2.618 + 3.14159) * helixRadius), 0.025);

  let bp7 = sdCapsule(p, vec3f(cos(3.14159) * helixRadius, 0.0, sin(3.14159) * helixRadius), vec3f(cos(3.14159 + 3.14159) * helixRadius, 0.0, sin(3.14159 + 3.14159) * helixRadius), 0.025);

  let bp8 = sdCapsule(p, vec3f(cos(3.665) * helixRadius, 0.3, sin(3.665) * helixRadius), vec3f(cos(3.665 + 3.14159) * helixRadius, 0.3, sin(3.665 + 3.14159) * helixRadius), 0.025);

  let bp9 = sdCapsule(p, vec3f(cos(4.189) * helixRadius, 0.6, sin(4.189) * helixRadius), vec3f(cos(4.189 + 3.14159) * helixRadius, 0.6, sin(4.189 + 3.14159) * helixRadius), 0.025);

  let bp10 = sdCapsule(p, vec3f(cos(4.712) * helixRadius, 0.9, sin(4.712) * helixRadius), vec3f(cos(4.712 + 3.14159) * helixRadius, 0.9, sin(4.712 + 3.14159) * helixRadius), 0.025);

  let bp11 = sdCapsule(p, vec3f(cos(5.236) * helixRadius, 1.2, sin(5.236) * helixRadius), vec3f(cos(5.236 + 3.14159) * helixRadius, 1.2, sin(5.236 + 3.14159) * helixRadius), 0.025);

  let bp12 = sdCapsule(p, vec3f(cos(5.76) * helixRadius, 1.5, sin(5.76) * helixRadius), vec3f(cos(5.76 + 3.14159) * helixRadius, 1.5, sin(5.76 + 3.14159) * helixRadius), 0.025);

  // === NUCLEOTIDE DETAILS - Small spheres at base pair ends ===
  // Adenine/Thymine and Guanine/Cytosine represented as spheres
  let nuc1a = sdSphere(p - vec3f(cos(0.0) * helixRadius, -1.8, sin(0.0) * helixRadius), 0.045);
  let nuc1b = sdSphere(p - vec3f(cos(3.14159) * helixRadius, -1.8, sin(3.14159) * helixRadius), 0.045);

  let nuc2a = sdSphere(p - vec3f(cos(0.524) * helixRadius, -1.5, sin(0.524) * helixRadius), 0.045);
  let nuc2b = sdSphere(p - vec3f(cos(0.524 + 3.14159) * helixRadius, -1.5, sin(0.524 + 3.14159) * helixRadius), 0.045);

  let nuc3a = sdSphere(p - vec3f(cos(1.047) * helixRadius, -1.2, sin(1.047) * helixRadius), 0.045);
  let nuc3b = sdSphere(p - vec3f(cos(1.047 + 3.14159) * helixRadius, -1.2, sin(1.047 + 3.14159) * helixRadius), 0.045);

  let nuc4a = sdSphere(p - vec3f(cos(1.571) * helixRadius, -0.9, sin(1.571) * helixRadius), 0.045);
  let nuc4b = sdSphere(p - vec3f(cos(1.571 + 3.14159) * helixRadius, -0.9, sin(1.571 + 3.14159) * helixRadius), 0.045);

  let nuc5a = sdSphere(p - vec3f(cos(2.094) * helixRadius, -0.6, sin(2.094) * helixRadius), 0.045);
  let nuc5b = sdSphere(p - vec3f(cos(2.094 + 3.14159) * helixRadius, -0.6, sin(2.094 + 3.14159) * helixRadius), 0.045);

  let nuc6a = sdSphere(p - vec3f(cos(2.618) * helixRadius, -0.3, sin(2.618) * helixRadius), 0.045);
  let nuc6b = sdSphere(p - vec3f(cos(2.618 + 3.14159) * helixRadius, -0.3, sin(2.618 + 3.14159) * helixRadius), 0.045);

  // Upper nucleotides
  let nuc7a = sdSphere(p - vec3f(cos(3.14159) * helixRadius, 0.0, sin(3.14159) * helixRadius), 0.045);
  let nuc7b = sdSphere(p - vec3f(cos(6.283) * helixRadius, 0.0, sin(6.283) * helixRadius), 0.045);

  let nuc8a = sdSphere(p - vec3f(cos(3.665) * helixRadius, 0.3, sin(3.665) * helixRadius), 0.045);
  let nuc8b = sdSphere(p - vec3f(cos(3.665 + 3.14159) * helixRadius, 0.3, sin(3.665 + 3.14159) * helixRadius), 0.045);

  let nuc9a = sdSphere(p - vec3f(cos(4.189) * helixRadius, 0.6, sin(4.189) * helixRadius), 0.045);
  let nuc9b = sdSphere(p - vec3f(cos(4.189 + 3.14159) * helixRadius, 0.6, sin(4.189 + 3.14159) * helixRadius), 0.045);

  let nuc10a = sdSphere(p - vec3f(cos(4.712) * helixRadius, 0.9, sin(4.712) * helixRadius), 0.045);
  let nuc10b = sdSphere(p - vec3f(cos(4.712 + 3.14159) * helixRadius, 0.9, sin(4.712 + 3.14159) * helixRadius), 0.045);

  let nuc11a = sdSphere(p - vec3f(cos(5.236) * helixRadius, 1.2, sin(5.236) * helixRadius), 0.045);
  let nuc11b = sdSphere(p - vec3f(cos(5.236 + 3.14159) * helixRadius, 1.2, sin(5.236 + 3.14159) * helixRadius), 0.045);

  let nuc12a = sdSphere(p - vec3f(cos(5.76) * helixRadius, 1.5, sin(5.76) * helixRadius), 0.045);
  let nuc12b = sdSphere(p - vec3f(cos(5.76 + 3.14159) * helixRadius, 1.5, sin(5.76 + 3.14159) * helixRadius), 0.045);

  // === END CAPS - Termination spheres ===
  // Bottom cap
  let bottomCap = sdSphere(p - vec3f(0.0, -2.0, 0.0), 0.1);
  // Top cap
  let topCap = sdSphere(p - vec3f(0.0, 2.0, 0.0), 0.1);

  // === BASE PLATFORM - For 3D print stability ===
  let base = sdCylinder(p - vec3f(0.0, -2.3, 0.0), 0.08, 0.5);

  // === COMBINE ALL ELEMENTS ===
  // Backbone strands
  let d1 = opSmoothUnion(strand1, strand2, 0.04);

  // Add base pairs
  let d2 = opSmoothUnion(d1, bp1, 0.03);
  let d3 = opSmoothUnion(d2, bp2, 0.03);
  let d4 = opSmoothUnion(d3, bp3, 0.03);
  let d5 = opSmoothUnion(d4, bp4, 0.03);
  let d6 = opSmoothUnion(d5, bp5, 0.03);
  let d7 = opSmoothUnion(d6, bp6, 0.03);
  let d8 = opSmoothUnion(d7, bp7, 0.03);
  let d9 = opSmoothUnion(d8, bp8, 0.03);
  let d10 = opSmoothUnion(d9, bp9, 0.03);
  let d11 = opSmoothUnion(d10, bp10, 0.03);
  let d12 = opSmoothUnion(d11, bp11, 0.03);
  let d13 = opSmoothUnion(d12, bp12, 0.03);

  // Add nucleotide spheres - lower half
  let d14 = opSmoothUnion(d13, nuc1a, 0.025);
  let d15 = opSmoothUnion(d14, nuc1b, 0.025);
  let d16 = opSmoothUnion(d15, nuc2a, 0.025);
  let d17 = opSmoothUnion(d16, nuc2b, 0.025);
  let d18 = opSmoothUnion(d17, nuc3a, 0.025);
  let d19 = opSmoothUnion(d18, nuc3b, 0.025);
  let d20 = opSmoothUnion(d19, nuc4a, 0.025);
  let d21 = opSmoothUnion(d20, nuc4b, 0.025);
  let d22 = opSmoothUnion(d21, nuc5a, 0.025);
  let d23 = opSmoothUnion(d22, nuc5b, 0.025);
  let d24 = opSmoothUnion(d23, nuc6a, 0.025);
  let d25 = opSmoothUnion(d24, nuc6b, 0.025);

  // Add nucleotide spheres - upper half
  let d26 = opSmoothUnion(d25, nuc7a, 0.025);
  let d27 = opSmoothUnion(d26, nuc7b, 0.025);
  let d28 = opSmoothUnion(d27, nuc8a, 0.025);
  let d29 = opSmoothUnion(d28, nuc8b, 0.025);
  let d30 = opSmoothUnion(d29, nuc9a, 0.025);
  let d31 = opSmoothUnion(d30, nuc9b, 0.025);
  let d32 = opSmoothUnion(d31, nuc10a, 0.025);
  let d33 = opSmoothUnion(d32, nuc10b, 0.025);
  let d34 = opSmoothUnion(d33, nuc11a, 0.025);
  let d35 = opSmoothUnion(d34, nuc11b, 0.025);
  let d36 = opSmoothUnion(d35, nuc12a, 0.025);
  let d37 = opSmoothUnion(d36, nuc12b, 0.025);

  // Add end caps
  let d38 = opSmoothUnion(d37, bottomCap, 0.05);
  let d39 = opSmoothUnion(d38, topCap, 0.05);

  // Add base platform
  let result = opSmoothUnion(d39, base, 0.06);

  return result;
}