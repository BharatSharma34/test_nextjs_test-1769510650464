"""
Shared LLM configuration for the application.
Supports OpenAI, Anthropic, and Gemini based on LLM_PROVIDER env variable.
"""
import os
from pathlib import Path
from dotenv import load_dotenv


def get_llm_config():
    """
    Load LLM configuration from .env file.
    Returns a dict with provider, api_key, and model.
    """
    root_dir = Path(__file__).resolve().parent.parent
    env_path = root_dir / ".env"
    load_dotenv(env_path, override=True)

    llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if llm_provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in .env. Set LLM_PROVIDER=anthropic and add your Anthropic API key.")
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        return {"provider": "anthropic", "api_key": api_key, "model": model}
    elif llm_provider == "openai":
        api_key = os.getenv("OPEN_API")
        if not api_key:
            raise ValueError("OPEN_API key not found in .env. Set LLM_PROVIDER=openai and add your OpenAI API key.")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        return {"provider": "openai", "api_key": api_key, "model": model}
    elif llm_provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env. Set LLM_PROVIDER=gemini and add your Gemini API key.")
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        return {"provider": "gemini", "api_key": api_key, "model": model}
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {llm_provider}. Use 'openai', 'anthropic', or 'gemini'.")


def get_llm_client(config=None, async_client=False):
    """
    Create and return an LLM client based on configuration.
    Returns a tuple: (client, provider_name)

    Args:
        config: Optional config dict. If None, loads from environment.
        async_client: If True, returns async client for OpenAI. Default False.
    """
    if config is None:
        config = get_llm_config()

    provider = config["provider"]
    api_key = config["api_key"]

    if provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        return client, "anthropic"
    elif provider == "openai":
        if async_client:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key)
        else:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
        return client, "openai"
    elif provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = config.get("model", "gemini-2.0-flash-exp")
        client = genai.GenerativeModel(model)
        return client, "gemini"
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def extract_token_usage(response, provider):
    """
    Extract token usage from LLM response.
    Returns a dict with input_tokens, output_tokens, and total_tokens.
    """
    if provider == "anthropic":
        # Anthropic response has usage attribute
        if hasattr(response, 'usage'):
            return {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
    elif provider == "openai":
        # OpenAI response has usage attribute
        if hasattr(response, 'usage'):
            return {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
    elif provider == "gemini":
        # Gemini response has usage_metadata attribute
        if hasattr(response, 'usage_metadata'):
            return {
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            }

    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


async def call_llm(messages, temperature=0, max_tokens=4096, json_mode=True):
    """
    Universal LLM calling function that works with OpenAI, Anthropic, and Gemini.

    Args:
        messages: List of message dicts with 'role' and 'content'
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        json_mode: Whether to request JSON output

    Returns:
        Response text as string
    """
    config = get_llm_config()
    client, provider = get_llm_client(config)
    model = config.get("model")

    if provider == "anthropic":
        # Claude API format
        # Filter out system messages and convert to Claude format
        claude_messages = []
        system_content = None

        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                claude_messages.append(msg)

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": claude_messages
        }

        if system_content:
            kwargs["system"] = system_content

        response = client.messages.create(**kwargs)
        return response.content[0].text

    elif provider == "openai":
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    elif provider == "gemini":
        # Gemini API format - convert messages to Gemini format
        gemini_messages = []
        system_instruction = None

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                gemini_messages.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                gemini_messages.append({"role": "model", "parts": [msg["content"]]})

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        # If we have a system instruction, recreate the client with it
        if system_instruction:
            import google.generativeai as genai
            client = genai.GenerativeModel(model, system_instruction=system_instruction)

        response = client.generate_content(
            gemini_messages,
            generation_config=generation_config
        )
        return response.text

    else:
        raise ValueError(f"Unsupported provider: {provider}")
