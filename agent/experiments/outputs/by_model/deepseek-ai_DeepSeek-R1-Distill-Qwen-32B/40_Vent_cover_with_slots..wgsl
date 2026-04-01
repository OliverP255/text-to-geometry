// Prompt: Vent cover with slots.
// Model: deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
// Generated WGSL SDF

fn map(p: vec3f) -> f32 {
  let plate = sdBox(p, vec3f(0.25, 0.05, 0.25));
  let q = opRepPolar(p, 4.0);
  let slot = sdBox(q - vec3f(0.25, 0.0, 0.0), vec3f(0.3, 0.025, 0.05));
  return opS(plate, slot);
}

Wait, but in the example, the hole was subtracted from the body. So, in this case, the slots are subtracted from the plate.

But I'm not sure if this will create four slots or just one. Because opRepPolar is applied to p, creating four points, but then slot is calculated for each. So, the distance field for slot would be the minimum distance to any of the four slots.

Wait, perhaps I should test this approach. Alternatively, maybe I should create a single slot and then repeat it.

Alternatively, perhaps I should create a single slot, then use opRepPolar on the slot's distance field. But I'm not sure how that works.

Wait, perhaps the correct approach is to create a single slot, then apply opRepPolar to the point before creating the slot. So, each repeated point is translated and a slot is created there.

So, the code would be:

let plate = sdBox(p, vec3f(0.25, 0.05, 0.25));
let q = opRepPolar(p, 4.0);
let slot = sdBox(q - vec3f(0.25, 0.0, 0.0), vec3f(0.3, 0.025, 0.05));
let slots = slot;
return opS(plate, slots);

But I'm not sure if this correctly creates four slots. Alternatively, perhaps I should create a single slot and then use opRepPolar on the slot's distance field.

Wait, perhaps the code should be:

let plate = sdBox(p, vec3f(0.25, 0.05, 0.25));
let slot = sdBox(p - vec3f(0.25, 0.0, 0.0), vec3f(0.3, 0.025, 0.05));
let slots = opRepPolar(slot, 4.0);
return opS(plate, slots);

No, because opRepPolar operates on the point, not on the distance field. So, I think the first approach is correct.

Wait, perhaps I should look at the example again. In the radial repeat example, the code was:

let body = sdCylinder(p, 0.1, 0.5);
let q = opRepPolar(p, 6.0);
let hole = sdCylinder