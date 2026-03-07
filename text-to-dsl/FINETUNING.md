
Finetuning LLM that generates the graphs, distilled Text->SDF model

THEN

Training "inverse model" to generate DAGs from SDFs using fine-tuned LLM graph output as training data.




Final representation (before lowering and then going to GPU) is DAG

LLM Code is working the best for CAD generation. 
Don't put an intimediary representations inbetween.

text → LLM codes program in my DSL script → FORMAL/LOWERED DAG → evaluate SDF

------------

I will be fine-tuning DeepSeek for Text->DSL Gen with the following:

Supervised fine-tuning:
(1) Grammar constrained decoding so it follows syntax of the DSL
(2) Scoring the geometric model it produced: Validity of geometry, node-count penalties, (loss could be calculated from optimiser as well)

Train from teacher Text->SDF Models (eg Diffusion-SDF):
(3) Determine loss from the SDF produced by the teacher model (what is the formula for this?)




