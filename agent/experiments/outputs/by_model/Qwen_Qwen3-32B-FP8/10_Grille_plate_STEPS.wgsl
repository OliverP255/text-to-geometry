// Prompt: Grille plate STEPS: 1) Plate sdBox (0.26, 0.032, 0.18). 2) For i=0..7 subtract slot sdBox (0.012, 0.04, 0.19) center at (-0.105 + i*0.03, 0, 0). Eight slots.
// Model: Qwen/Qwen3-32B-FP8
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let plate = sdBox(p, vec3f(0.26, 0.032, 0.18));
  
  let x0 = -0.105;
  let x1 = x0 + 0.03;
  let x2 = x1 + 0.03;
  let x3 = x2 + 0.03;
  let x4 = x3 + 0.03;
  let x5 = x4 + 0.03;
  let x6 = x5 + 0.03;
  let x7 = x6 + 0.03;
  
  let s0 = sdBox(p - vec3f(x0, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s1 = sdBox(p - vec3f(x1, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s2 = sdBox(p - vec3f(x2, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s3 = sdBox(p - vec3f(x3, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s4 = sdBox(p - vec3f(x4, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s5 = sdBox(p - vec3f(x5, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s6 = sdBox(p - vec3f(x6, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  let s7 = sdBox(p - vec3f(x7, 0.0, 0.0), vec3f(0.012, 0.04, 0.19));
  
  let d0 = opS(plate, s0);
  let d1 = opS(d0, s1);
  let d2 = opS(d1, s2);
  let d3 = opS(d2, s3);
  let d4 = opS(d3, s4);
  let d5 = opS(d4, s5);
  let d6 = opS(d5, s6);
  let d7 = opS(d6, s7);
  
  return d7;
}