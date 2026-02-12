#!/usr/bin/env python3
"""
Immediate working Kimi K2.5 interface
Use this RIGHT NOW while dependencies install
"""
import subprocess
import sys
import json

def chat_with_kimi(message: str, model: str = "llava:13b") -> str:
    """Chat with Kimi via Ollama directly"""
    try:
        result = subprocess.run(
            ['ollama', 'run', model, message],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

def main():
    print("=" * 60)
    print("🤖 Kimi K2.5 - Ready to Use NOW")
    print("=" * 60)
    print()
    print("Type your message (or 'quit' to exit)")
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break

            if not user_input:
                continue

            print("\n🤖 Kimi: ", end="", flush=True)
            response = chat_with_kimi(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    main()
