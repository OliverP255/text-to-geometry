Fine-tune deepseek coder or whatever is best low-level llm coder
Use QLoRa adapter
Use Grammar constrained decoding
Use text->DSL pairs
Eg
Build up from easy DSL to harder DSL outputs
Multiple paraphrased prompts for same output
 wrong DSL -> corrected DSL


Then score geometry by node count etc.


GRAMMAR AND SYNTAX LEARNING
Use grammar constrained decoding so it follows syntax of the DSL
Train on synthetic dataset of good DSL


GEOMETRY FINETUNING
Just make DAG differentiable
LLM proposes idea. You reduce loss at DAG level then return DSL back for LLM to learn.





Train from teacher Text->SDF Models (eg Diffusion-SDF):
(2) Scoring the geometric model it produced: Validity of geometry, node-count penalties, (loss could be calculated from optimiser as well)
(3) Determine loss from the SDF produced by the teacher model (what is the formula for this?)

