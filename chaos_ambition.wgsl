fn map(p: vec3f) -> f32 {
  // Noise for organic variation
  let n = fract(sin(dot(p, vec3f(12.9898, 78.233, 45.164))) * 43758.5453);
  let n2 = fract(sin(dot(p * 1.7, vec3f(45.164, 12.9898, 78.233))) * 43758.5453);

  // === CENTRAL CORE - Ambition's spine ===
  // Main ascending form - tapered, twisted
  let twist = p.y * 0.6;
  let coreP = opRotateY(p, twist);
  let coreRadius = 0.18 + 0.08 * sin(p.y * 2.5);
  let core = sdCylinder(coreP - vec3f(0.0, 0.8, 0.0), 1.6, coreRadius);

  // Core surface detail - carved channels spiraling up
  let channelAngle = p.y * 3.0;
  let channelP = coreP - vec3f(cos(channelAngle) * coreRadius * 0.7, 0.0, sin(channelAngle) * coreRadius * 0.7);
  let channel = sdCylinder(channelP, 1.5, 0.03);
  let coreCarved = opSmoothSubtraction(core, channel, 0.02);

  // === ASCENDING HELIXES - Ambition reaching up ===
  // Triple helix wrapping the core
  let h1Angle = p.y * 2.0;
  let h1R = 0.35 + 0.05 * sin(p.y * 1.5);
  let helix1 = sdCylinder(p - vec3f(cos(h1Angle) * h1R, 0.0, sin(h1Angle) * h1R), 1.4, 0.05);

  let h2Angle = p.y * 2.0 + 2.094;
  let helix2 = sdCylinder(p - vec3f(cos(h2Angle) * h1R, 0.0, sin(h2Angle) * h1R), 1.4, 0.05);

  let h3Angle = p.y * 2.0 + 4.189;
  let helix3 = sdCylinder(p - vec3f(cos(h3Angle) * h1R, 0.0, sin(h3Angle) * h1R), 1.4, 0.05);

  // === BRANCHING STRUCTURES - Growth emerging ===
  // Lower branches curving outward and up
  let branch1Base = p - vec3f(0.3, 0.2, 0.0);
  let branch1 = sdCapsule(branch1Base, vec3f(0.0), vec3f(0.4, 0.5, 0.2), 0.04);

  let branch2Base = p - vec3f(-0.25, 0.3, 0.2);
  let branch2 = sdCapsule(branch2Base, vec3f(0.0), vec3f(-0.35, 0.6, 0.15), 0.035);

  let branch3Base = p - vec3f(0.1, 0.15, -0.3);
  let branch3 = sdCapsule(branch3Base, vec3f(0.0), vec3f(0.2, 0.4, -0.35), 0.03);

  // Upper branches reaching higher
  let branch4Base = p - vec3f(0.2, 1.3, 0.15);
  let branch4 = sdCapsule(branch4Base, vec3f(0.0), vec3f(0.3, 0.4, 0.1), 0.035);

  let branch5Base = p - vec3f(-0.15, 1.4, -0.1);
  let branch5 = sdCapsule(branch5Base, vec3f(0.0), vec3f(-0.25, 0.35, -0.15), 0.03);

  // === CHAOS ELEMENTS - Fracture and disorder ===
  // Gyroid lattice embedded in lower section - but connected to core
  let gp = p * 2.2;
  let gyroid = abs(dot(sin(gp), cos(gp.zxy))) / 2.2 - 0.04;
  let gyroidMask = sdBox(p - vec3f(0.0, -0.1, 0.0), vec3f(0.5, 0.45, 0.5));
  let gyroidSection = opSmoothIntersection(gyroid, gyroidMask, 0.06);

  // Fracture shards - all attached to main form
  let shard1P = opRotateX(opRotateY(p - vec3f(0.45, 0.5, 0.25), 1.2), 0.5);
  let shard1 = sdBox(shard1P, vec3f(0.03, 0.12, 0.025));

  let shard2P = opRotateX(opRotateY(p - vec3f(-0.35, 0.65, 0.3), 2.5), -0.4);
  let shard2 = sdBox(shard2P, vec3f(0.035, 0.1, 0.03));

  let shard3P = opRotateX(opRotateY(p - vec3f(0.2, 0.8, -0.4), 0.8), 0.3);
  let shard3 = sdBox(shard3P, vec3f(0.025, 0.14, 0.02));

  // === CROWN - Ambition's peak ===
  // Main crown sphere with surface turbulence
  let crownSphere = sdSphere(p - vec3f(0.0, 1.8, 0.0), 0.28);
  let crown = crownSphere - n * 0.04;

  // Crown protrusions - like flames or aspirations
  let flame1 = sdCapsule(p - vec3f(0.0, 1.9, 0.0), vec3f(0.0), vec3f(0.12, 0.22, 0.05), 0.04);
  let flame2 = sdCapsule(p - vec3f(0.0, 1.92, 0.0), vec3f(0.0), vec3f(-0.1, 0.2, -0.08), 0.035);
  let flame3 = sdCapsule(p - vec3f(0.0, 1.88, 0.0), vec3f(0.0), vec3f(0.05, 0.18, -0.1), 0.03);
  let flame4 = sdCapsule(p - vec3f(0.0, 1.91, 0.0), vec3f(0.0), vec3f(-0.08, 0.15, 0.12), 0.032);

  // === BASE - Foundation ===
  // Stable base with organic edge
  let baseCore = sdCylinder(p - vec3f(0.0, -1.2, 0.0), 0.18, 0.35);
  let base = baseCore - n2 * 0.02;

  // Base rim - slight flare
  let baseRim = sdTorus(p - vec3f(0.0, -1.35, 0.0), vec2f(0.3, 0.04));

  // === CONNECT EVERYTHING ===
  // Start with core structure
  let d1 = opSmoothUnion(coreCarved, helix1, 0.08);
  let d2 = opSmoothUnion(d1, helix2, 0.08);
  let d3 = opSmoothUnion(d2, helix3, 0.08);

  // Add branches
  let d4 = opSmoothUnion(d3, branch1, 0.05);
  let d5 = opSmoothUnion(d4, branch2, 0.05);
  let d6 = opSmoothUnion(d5, branch3, 0.05);
  let d7 = opSmoothUnion(d6, branch4, 0.045);
  let d8 = opSmoothUnion(d7, branch5, 0.045);

  // Add chaos elements
  let d9 = opSmoothUnion(d8, gyroidSection, 0.06);
  let d10 = opSmoothUnion(d9, shard1, 0.04);
  let d11 = opSmoothUnion(d10, shard2, 0.04);
  let d12 = opSmoothUnion(d11, shard3, 0.04);

  // Add crown
  let d13 = opSmoothUnion(d12, crown, 0.1);
  let d14 = opSmoothUnion(d13, flame1, 0.05);
  let d15 = opSmoothUnion(d14, flame2, 0.045);
  let d16 = opSmoothUnion(d15, flame3, 0.04);
  let d17 = opSmoothUnion(d16, flame4, 0.042);

  // Add base - final connection
  let d18 = opSmoothUnion(d17, base, 0.08);
  let result = opSmoothUnion(d18, baseRim, 0.05);

  return result;
}