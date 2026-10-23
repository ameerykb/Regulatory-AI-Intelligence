"""
Local LLM service for regulatory intelligence.

Connects to Qwen2.5 through Ollama's local API.
No paid API key is required.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"


def generate_llm_response(prompt: str) -> str:
    """Generate a response using the local Qwen LLM."""

    if not isinstance(prompt, str):
        raise TypeError("Prompt must be a string.")

    if not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
        },
    }

    request = Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(
            f"Unable to communicate with Ollama: {error}"
        ) from error

    answer = result.get("response")

    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError(
            "Ollama returned an empty or invalid response."
        )

    return answer.strip()


def generate_chat_response(
    system_message: str,
    user_message: str,
) -> str:
    """Generate a response using Ollama's chat API."""

    if not isinstance(system_message, str) or not system_message.strip():
        raise ValueError("System message cannot be empty.")

    if not isinstance(user_message, str) or not user_message.strip():
        raise ValueError("User message cannot be empty.")

    chat_url = "http://localhost:11434/api/chat"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
        },
    }

    request = Request(
        chat_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(
            f"Unable to communicate with Ollama chat API: {error}"
        ) from error

    message = result.get("message", {})
    answer = message.get("content")

    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError(
            "Ollama chat API returned an empty or invalid response."
        )

    return answer.strip()

