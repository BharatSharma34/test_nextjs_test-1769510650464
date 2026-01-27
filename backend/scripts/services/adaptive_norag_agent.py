"""
Adaptive NoRAG Agent

Implements intelligent, iterative index loading for NoRAG queries.
The agent starts with minimal indices and requests more only when needed.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

from llm_config import get_llm_config, get_llm_client
from scripts.services.index_metadata import INDEX_CAPABILITIES, format_capabilities_for_prompt


MAX_ITERATIONS = 3  # Prevent infinite loops


def load_index(doc_output_dir: Path, index_type: str) -> Dict:
    """Load a single index JSON file."""
    index_path = doc_output_dir / f"{index_type}.json"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def build_adaptive_prompt(
    normalized_query: str,
    loaded_indices: Dict[str, Dict],
    available_indices: List[str],
    iteration: int
) -> str:
    """
    Build the prompt for the adaptive NoRAG agent.

    The prompt includes:
    - Index capabilities documentation
    - Currently loaded indices
    - Instructions for requesting additional indices
    - The user's query
    """

    # Format which indices are currently loaded
    loaded_list = list(loaded_indices.keys())
    not_loaded = [idx for idx in available_indices if idx not in loaded_list]

    prompt = f"""You are an adaptive document analysis assistant using index graph metadata.

{format_capabilities_for_prompt()}

CURRENTLY LOADED INDICES:
{', '.join(loaded_list) if loaded_list else 'None yet'}

NOT YET LOADED (but available):
{', '.join(not_loaded) if not_loaded else 'None - all loaded'}

INDEX DATA:
{json.dumps(loaded_indices, indent=2)}

=" * 80

INSTRUCTIONS:

1. Analyze the user's query and the metadata in the currently loaded indices.

2. Use the metadata to make INFERENCES and CONNECTIONS:
   - Synthesize information from multiple nodes
   - Draw logical conclusions from summaries and keywords
   - Connect related concepts across different sections
   - Use scope information (pages, sections) to understand coverage

3. Determine if you can answer the query with current indices:

   CAN ANSWER IF:
   - The metadata provides sufficient information
   - You can make reasonable inferences from summaries and keywords
   - The query is high-level or navigational
   - You can synthesize an answer from multiple nodes

   NEED MORE INDICES IF:
   - The query asks about topics not covered in current metadata
   - You need specific details that aren't in the summaries
   - The query spans domains not represented in current indices
   - Additional context would significantly improve the answer

4. If you need additional indices, respond EXACTLY in this format:

REQUEST_INDICES: ["index_name1", "index_name2"]
REASONING: Brief explanation of why these indices are needed and what they'll provide

5. Otherwise, provide your answer directly using markdown formatting:
   - Use headers (##, ###) to structure your answer
   - Use bullet lists for items
   - Use **bold** for emphasis
   - Be confident and comprehensive
   - Synthesize information from multiple nodes when appropriate
   - Make reasonable inferences based on the metadata

IMPORTANT:
- DO NOT be overly cautious - TRUST and USE the metadata
- DO NOT suggest RAG unless query requires exact quotes or specific page text
- DO NOT request indices you don't truly need
- DO make intelligent inferences from the available metadata
- This is iteration {iteration + 1} of {MAX_ITERATIONS} maximum

USER QUERY: {normalized_query}

YOUR RESPONSE:"""

    return prompt


def parse_index_request(response_text: str) -> Tuple[bool, List[str], str]:
    """
    Parse LLM response to check if it's requesting additional indices.

    Returns:
        (is_request, requested_indices, reasoning_or_answer)
    """
    # Check for REQUEST_INDICES pattern
    request_match = re.search(r'REQUEST_INDICES:\s*\[(.*?)\]', response_text, re.DOTALL)
    reasoning_match = re.search(r'REASONING:\s*(.*?)(?:\n\n|$)', response_text, re.DOTALL)

    if request_match:
        # Parse the list of index names
        indices_str = request_match.group(1)
        # Extract quoted strings
        indices = re.findall(r'["\']([^"\']+)["\']', indices_str)

        reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"

        return True, indices, reasoning

    # Not a request - this is the answer
    return False, [], response_text


def call_llm_with_prompt(prompt: str) -> str:
    """Make an LLM call with the given prompt."""
    try:
        config = get_llm_config()
        client, provider = get_llm_client(config)
        model = config.get("model")

        if provider == "anthropic":
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()

        elif provider == "openai":
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an adaptive document analysis assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_completion_tokens=4000
                )
            except Exception as e:
                if "max_completion_tokens" in str(e):
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are an adaptive document analysis assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=4000
                    )
                else:
                    raise
            return response.choices[0].message.content.strip()

        elif provider == "gemini":
            import google.generativeai as genai
            generation_config = {
                "temperature": 0.3,
                "max_output_tokens": 4000
            }
            response = client.generate_content(
                [{"role": "user", "parts": [prompt]}],
                generation_config=generation_config
            )
            return response.text.strip()

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    except Exception as e:
        raise Exception(f"LLM call failed: {str(e)}")


def execute_adaptive_norag(
    normalized_query: str,
    doc_output_dir: Path,
    initial_indices: List[str],
    available_indices: List[str]
) -> Dict[str, Any]:
    """
    Execute the adaptive NoRAG workflow.

    Starts with initial_indices and iteratively loads more if the LLM requests them.

    Args:
        normalized_query: The clarified user query
        doc_output_dir: Path to document's JSON output directory
        initial_indices: Starting indices to load
        available_indices: All indices that exist for this document

    Returns:
        Result dict with answer and metadata
    """
    loaded_indices = {}
    iteration_history = []

    # Load initial indices
    print(f"[Adaptive NoRAG] Starting with indices: {initial_indices}")
    for index_type in initial_indices:
        data = load_index(doc_output_dir, index_type)
        if data:
            loaded_indices[index_type] = data
            print(f"[Adaptive NoRAG] Loaded {index_type}")

    if not loaded_indices:
        return {
            "success": False,
            "error": "No initial indices could be loaded",
            "answer": "I couldn't find the necessary index graphs to answer your question."
        }

    # Iterative refinement loop
    for iteration in range(MAX_ITERATIONS):
        print(f"\n[Adaptive NoRAG] Iteration {iteration + 1}/{MAX_ITERATIONS}")
        print(f"[Adaptive NoRAG] Currently loaded: {list(loaded_indices.keys())}")

        # Build prompt with current state
        prompt = build_adaptive_prompt(
            normalized_query,
            loaded_indices,
            available_indices,
            iteration
        )

        # Call LLM
        response = call_llm_with_prompt(prompt)

        # Parse response
        is_request, requested_indices, content = parse_index_request(response)

        iteration_history.append({
            "iteration": iteration + 1,
            "loaded_indices": list(loaded_indices.keys()),
            "is_request": is_request,
            "requested_indices": requested_indices if is_request else None,
            "reasoning": content if is_request else None
        })

        if not is_request:
            # Got the final answer
            print(f"[Adaptive NoRAG] Answer generated after {iteration + 1} iteration(s)")
            return {
                "success": True,
                "answer": content,
                "metadata": {
                    "workflow": "norag_adaptive",
                    "indices_used": list(loaded_indices.keys()),
                    "iterations": iteration + 1,
                    "iteration_history": iteration_history
                }
            }

        # LLM is requesting additional indices
        print(f"[Adaptive NoRAG] Requesting additional indices: {requested_indices}")
        print(f"[Adaptive NoRAG] Reasoning: {content}")

        # Load requested indices
        newly_loaded = []
        for index_type in requested_indices:
            if index_type in loaded_indices:
                print(f"[Adaptive NoRAG] {index_type} already loaded, skipping")
                continue

            if index_type not in available_indices:
                print(f"[Adaptive NoRAG] {index_type} not available, skipping")
                continue

            data = load_index(doc_output_dir, index_type)
            if data:
                loaded_indices[index_type] = data
                newly_loaded.append(index_type)
                print(f"[Adaptive NoRAG] Loaded {index_type}")

        if not newly_loaded:
            print(f"[Adaptive NoRAG] No new indices loaded, stopping iteration")
            # No new indices loaded, return current response as answer
            return {
                "success": True,
                "answer": f"**Note:** The system requested additional indices but they were not available.\n\n{content}",
                "metadata": {
                    "workflow": "norag_adaptive",
                    "indices_used": list(loaded_indices.keys()),
                    "iterations": iteration + 1,
                    "iteration_history": iteration_history
                }
            }

    # Max iterations reached
    print(f"[Adaptive NoRAG] Max iterations reached, returning last response")
    return {
        "success": True,
        "answer": f"**Note:** Maximum iterations reached. Here's what I found:\n\n{content}",
        "metadata": {
            "workflow": "norag_adaptive",
            "indices_used": list(loaded_indices.keys()),
            "iterations": MAX_ITERATIONS,
            "iteration_history": iteration_history,
            "max_iterations_reached": True
        }
    }
