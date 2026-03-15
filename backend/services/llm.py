import json
import os

from openai import AzureOpenAI

_client: AzureOpenAI | None = None


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        )
    return _client


def chat_json(system_prompt: str, user_prompt: str) -> dict:
    """Send a chat completion request and parse the response as JSON."""
    client = _get_client()
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    response = client.chat.completions.create(
        model=deployment,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    content = response.choices[0].message.content or "{}"
    return json.loads(content)
