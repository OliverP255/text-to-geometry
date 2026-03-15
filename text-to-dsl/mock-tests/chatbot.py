#!/usr/bin/env python3
"""
DSL-only CLI: grammar-constrained DSL generation via GLM-4.7-Flash.
Usage: python chatbot.py

Prompts for shape descriptions, generates DSL via inference.generate_dsl(),
outputs to terminal and writes to chatbot-output.dsl and chatbot-output.pkl.
POSTs DSL to server (SCENE_SERVER_URL) for rendering. Type 'quit' or 'exit' to stop.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Add build/ and text-to-dsl/ for t2g and inference
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "build"))
sys.path.insert(0, str(_root / "text-to-dsl"))

import text_to_geometry_bindings as t2g
from inference import generate_dsl, load_llm, warmup_prefix_cache

OUTPUT_DIR = Path(__file__).resolve().parent
DSL_PATH = OUTPUT_DIR / "chatbot-output.dsl"
FLATIR_PATH = OUTPUT_DIR / "chatbot-output.pkl"
SERVER_URL = os.environ.get("SCENE_SERVER_URL", "http://localhost:5001/scene")


def main() -> None:
    model_id = "mratsim/GLM-4.7-Flash-FP8"
    print(f"Loading model {model_id}...")
    llm = load_llm(model_id=model_id)
    print("Warming up prefix cache...")
    warmup_prefix_cache(llm)
    print("Ready. Describe a shape. Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            prompt = input("Describe shape: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not prompt:
            continue
        if prompt.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break

        dsl = generate_dsl(prompt, model_id=model_id, llm=llm)
        print(f"\nDSL:\n{dsl}\n")

        DSL_PATH.write_text(dsl)

        try:
            flatir = t2g.compile(dsl)
            flatir_bytes = t2g.serialize(flatir)
            FLATIR_PATH.write_bytes(flatir_bytes)
            print(f"Wrote {DSL_PATH}")
            print(f"Wrote {FLATIR_PATH}")
        except ValueError as e:
            print(f"Compile error: {e}", file=sys.stderr)
            print("DSL written to file; FlatIR not updated.", file=sys.stderr)
            continue

        data = json.dumps({"dsl": dsl}).encode("utf-8")
        req = urllib.request.Request(
            SERVER_URL,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                print("Posted to server; scene updated.")
        except urllib.error.URLError as e:
            print(f"Server POST failed: {e}", file=sys.stderr)

with open("mock-dsl.txt", "r") as f:
    dsl = f.read()
    req = json.dumps({"dsl": dsl}).encode("utf-8")
    req = urllib.request.Request(
        SERVER_URL,
        data=req,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("Posted to server; scene updated.")
except urllib.error.URLError as e:
        print(f"Server POST failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()

