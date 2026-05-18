fn map(p: vec3f) -> f32 {
    let cylR = 0.8;
    let cylH = 1.0;
    let wallT = 0.05;

    // --- Open-ended shell: subtract taller inner cylinder to cut off caps ---
    let dOuter = sdCylinder(p, cylH, cylR);
    let dInner = sdCylinder(p, cylH + 0.01, cylR - wallT);
    let dWall = opS(dOuter, dInner);

    // --- Gyroid infill ---
    let freq = 10.0;
    let gp = p * freq;
    let g = sin(gp.x) * cos(gp.y) + sin(gp.y) * cos(gp.z) + sin(gp.z) * cos(gp.x);
    let strutT = 0.12;
    let dGyroid = (abs(g) - strutT) / (freq * 1.5);

    // Clip gyroid to interior
    let dInterior = sdCylinder(p, cylH - wallT * 0.5, cylR - wallT);
    let dFill = opI(dGyroid, dInterior);

    return opU(dWall, dFill);
}