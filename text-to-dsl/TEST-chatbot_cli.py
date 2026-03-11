#!/usr/bin/env python3
"""
Simple chatbot CLI for GLM-4.7-Flash. Single-file, temporary.
Usage: python chatbot_cli.py
"""

from vllm import LLM
from vllm.sampling_params import SamplingParams
from transformers import AutoTokenizer


def main() -> None:
    model_id = "zai-org/GLM-4.7-Flash"
    print(f"Loading {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    llm = LLM(model=model_id, trust_remote_code=True, max_model_len=8192)

    sampling = SamplingParams(
        max_tokens=512,
        temperature=0.7,
        top_p=0.95,
        repetition_penalty=1.05,
    )

    messages: list[dict[str, str]] = []

    print("Chat with GLM-4.7-Flash. Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break

        messages.append({"role": "user", "content": user_input})
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        outputs = llm.generate(prompts=[prompt], sampling_params=sampling)
        reply = outputs[0].outputs[0].text.strip()

        messages.append({"role": "assistant", "content": reply})
        print(f"\nAssistant: {reply}\n")


if __name__ == "__main__":
    main()
