"""
Query Agent: Handles query classification and workflow routing.

Implements the agentic workflow for document querying:
1. Classify and normalize user queries
2. Route to NoRAG or RAG workflow
3. Execute appropriate retrieval and response generation
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from llm_config import get_llm_config, get_llm_client
from scripts.services.adaptive_norag_agent import execute_adaptive_norag


def classify_user_query(
    user_query: str,
    document_name: str,
    chat_history: List[Dict],
    available_indices: List[str]
) -> Dict[str, Any]:
    """
    Step 1: Classify and normalize the user's query.

    Uses LLM to analyze the query and determine:
    - Normalized/clarified query text
    - Query type and complexity
    - Workflow (RAG vs NoRAG)
    - Suggested indices to use

    Args:
        user_query: The raw user input
        document_name: Name of the document being queried
        chat_history: Previous conversation messages
        available_indices: List of available index files

    Returns:
        Classification result with workflow determination
    """
    base_dir = Path(__file__).parent.parent.parent
    prompt_path = base_dir / "inputs" / "promtps" / "query_classification.txt"

    # Load classification prompt
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Build context for LLM
    context_data = {
        "user_query": user_query,
        "document_name": document_name,
        "available_indices": available_indices,
        "chat_history_length": len(chat_history),
        "has_previous_context": len(chat_history) > 0
    }

    # Add recent chat context if available
    if chat_history:
        recent_messages = chat_history[-3:]  # Last 3 messages
        context_data["recent_context"] = [
            {
                "role": msg.get("role"),
                "content": msg.get("content")[:200]  # Truncate for brevity
            }
            for msg in recent_messages
        ]

    user_message = f"""{prompt_template}

DOCUMENT CONTEXT:
{json.dumps(context_data, indent=2)}

USER QUERY: "{user_query}"

Analyze this query and return your classification as JSON."""

    # Call LLM
    try:
        config = get_llm_config()
        client, provider = get_llm_client(config)
        model = config.get("model")

        if provider == "anthropic":
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=0,
                messages=[{"role": "user", "content": user_message}]
            )
            result_text = response.content[0].text.strip()

        elif provider == "openai":
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an expert document query classifier."},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0,
                    response_format={"type": "json_object"},
                    max_completion_tokens=2000
                )
            except Exception as e:
                if "max_completion_tokens" in str(e):
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are an expert document query classifier."},
                            {"role": "user", "content": user_message}
                        ],
                        temperature=0,
                        response_format={"type": "json_object"},
                        max_tokens=2000
                    )
                else:
                    raise
            result_text = response.choices[0].message.content.strip()

        elif provider == "gemini":
            import google.generativeai as genai
            generation_config = {
                "temperature": 0,
                "max_output_tokens": 2000,
                "response_mime_type": "application/json"
            }
            response = client.generate_content(
                [{"role": "user", "parts": [user_message]}],
                generation_config=generation_config
            )
            result_text = response.text.strip()

        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Parse JSON response
        classification = json.loads(result_text)

        return {
            "success": True,
            "classification": classification,
            "provider": provider,
            "model": model
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "fallback_classification": {
                "normalized_query": user_query,
                "original_query": user_query,
                "query_type": "unknown",
                "complexity": "moderate",
                "workflow": "rag",  # Default to RAG for safety
                "confidence": 0.5,
                "reasoning": f"Classification failed: {str(e)}. Defaulting to RAG workflow.",
                "suggested_indices": ["index_section", "index_topic"],
                "expected_answer_type": "general",
                "retrieval_scope": {
                    "broad": True,
                    "specific_sections": [],
                    "keywords": []
                }
            }
        }


def execute_norag_workflow(
    normalized_query: str,
    document_name: str,
    suggested_indices: List[str],
    chat_history: List[Dict]
) -> Dict[str, Any]:
    """
    Step 2a: Execute Adaptive NoRAG workflow.

    Uses index graph metadata with intelligent, iterative loading.
    Starts with suggested indices and loads more if needed.

    Args:
        normalized_query: The clarified query from classification
        document_name: Name of the document
        suggested_indices: Initial indices to load
        chat_history: Previous conversation

    Returns:
        Answer with metadata
    """
    base_dir = Path(__file__).parent.parent.parent
    output_dir = base_dir / "outputs"

    # Sanitize document name for path
    safe_doc_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in document_name])
    doc_output_dir = output_dir / safe_doc_name / "json"

    # Check what indices are available
    available_indices = []
    for index_type in ["index_chapter", "index_file", "index_topic", "index_section", "index_reference"]:
        index_path = doc_output_dir / f"{index_type}.json"
        if index_path.exists():
            available_indices.append(index_type)

    print(f"[NoRAG] Available indices: {available_indices}")
    print(f"[NoRAG] Starting with: {suggested_indices}")

    # Execute adaptive NoRAG workflow
    try:
        result = execute_adaptive_norag(
            normalized_query=normalized_query,
            doc_output_dir=doc_output_dir,
            initial_indices=suggested_indices,
            available_indices=available_indices
        )

        # Add provider info
        config = get_llm_config()
        _, provider = get_llm_client(config)
        model = config.get("model")

        if result["success"]:
            result["metadata"]["provider"] = provider
            result["metadata"]["model"] = model

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "answer": f"I encountered an error generating the response: {str(e)}"
        }


def execute_rag_workflow(
    normalized_query: str,
    document_name: str,
    suggested_indices: List[str],
    chat_history: List[Dict]
) -> Dict[str, Any]:
    """
    Step 2b: Execute RAG workflow.

    Phase 1: Generates a Weaviate retrieval plan (not yet executing)
    Phase 2: Will execute retrieval and generate answer

    Args:
        normalized_query: The clarified query from classification
        document_name: Name of the document
        suggested_indices: Which index files to guide retrieval
        chat_history: Previous conversation

    Returns:
        Retrieval plan and metadata
    """
    base_dir = Path(__file__).parent.parent.parent
    output_dir = base_dir / "outputs"
    prompt_dir = base_dir / "inputs" / "promtps"

    # Sanitize document name for path
    safe_doc_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in document_name])
    doc_output_dir = output_dir / safe_doc_name / "json"

    # Load suggested indices to guide retrieval planning
    loaded_indices = {}
    for index_type in suggested_indices:
        index_path = doc_output_dir / f"{index_type}.json"
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                loaded_indices[index_type] = json.load(f)

    print(f"[RAG] Generating retrieval plan with indices: {list(loaded_indices.keys())}")

    # Load retrieval plan prompt
    plan_prompt_path = prompt_dir / "rag_retrieval_plan.txt"
    with open(plan_prompt_path, "r", encoding="utf-8") as f:
        plan_prompt_template = f.read()

    # Format index metadata for prompt
    index_metadata_text = json.dumps(loaded_indices, indent=2) if loaded_indices else "No indices loaded"

    # Build full prompt
    user_message = plan_prompt_template.replace("{index_metadata}", index_metadata_text)
    user_message += f"\n\nUSER QUERY: {normalized_query}\n\nGenerate the retrieval plan as JSON:"

    try:
        config = get_llm_config()
        client, provider = get_llm_client(config)
        model = config.get("model")

        print(f"[RAG] Calling LLM to generate retrieval plan...")

        if provider == "anthropic":
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                temperature=0,
                messages=[{"role": "user", "content": user_message}]
            )
            plan_json = response.content[0].text.strip()

        elif provider == "openai":
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an expert at designing Weaviate retrieval plans."},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0,
                    response_format={"type": "json_object"},
                    max_completion_tokens=4000
                )
            except Exception as e:
                if "max_completion_tokens" in str(e):
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are an expert at designing Weaviate retrieval plans."},
                            {"role": "user", "content": user_message}
                        ],
                        temperature=0,
                        response_format={"type": "json_object"},
                        max_tokens=4000
                    )
                else:
                    raise
            plan_json = response.choices[0].message.content.strip()

        elif provider == "gemini":
            import google.generativeai as genai
            generation_config = {
                "temperature": 0,
                "max_output_tokens": 4000,
                "response_mime_type": "application/json"
            }
            response = client.generate_content(
                [{"role": "user", "parts": [user_message]}],
                generation_config=generation_config
            )
            plan_json = response.text.strip()

        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Parse the plan
        retrieval_plan = json.loads(plan_json)
        print(f"[RAG] Retrieval plan generated: {retrieval_plan.get('strategy')} strategy, {len(retrieval_plan.get('steps', []))} steps")

        return {
            "success": True,
            "answer": f"""## Retrieval Plan Generated

**Query:** {normalized_query}

**Why RAG is needed:** {retrieval_plan.get('reasoning', 'No reasoning provided')}

**Strategy:** {retrieval_plan.get('strategy', 'unknown')}

**Estimated Tokens:** {retrieval_plan.get('estimated_tokens', 'unknown'):,}

### Retrieval Steps:

{chr(10).join([f"**Step {i+1}:** {step.get('step_description', 'No description')}" for i, step in enumerate(retrieval_plan.get('steps', []))])}

---

**Note:** This is a retrieval plan only. Weaviate execution is not yet implemented. The plan shows what would be retrieved and how, providing transparency into the RAG process.""",
            "metadata": {
                "workflow": "rag_plan_generated",
                "retrieval_plan": retrieval_plan,
                "indices_used": list(loaded_indices.keys()),
                "provider": provider,
                "model": model,
                "status": "plan_only_not_executed"
            }
        }

    except Exception as e:
        print(f"[RAG] Error generating retrieval plan: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "answer": f"I encountered an error generating the retrieval plan: {str(e)}"
        }
