import logging
from groq import AsyncGroq
from app.core.config import settings

logger = logging.getLogger(__name__)


async def generate_chat_completion(
    prompt: str,
    system_prompt: str | None = None,
    json_mode: bool = False
) -> str:
    """
    Asynchronously queries Groq completions endpoint.

    Args:
        prompt: The main user text prompt.
        system_prompt: Optional system instruction prompt.
        json_mode: If True, forces Groq to output valid JSON by adding type: "json_object"
                   to response_format.

    Returns:
        The text response content from the configured Groq LLM (e.g. GPT-OSS).
    """
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in configurations.")

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response_format = {"type": "json_object"} if json_mode else None

    logger.info(f"Submitting chat completion request to Groq using model: {settings.GROQ_LLM_MODEL}")

    response = await client.chat.completions.create(
        model=settings.GROQ_LLM_MODEL,
        messages=messages,
        response_format=response_format,
        temperature=0.1,  # Low temperature for stable/deterministic analysis
    )

    content = response.choices[0].message.content
    return content
