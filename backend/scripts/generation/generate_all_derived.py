#!/usr/bin/env python3
"""
Generate all derived graphs from master.json in sequence.
Tracks and returns token usage for all operations.
"""
import json
import sys
from pathlib import Path
from llm_config import get_llm_config, get_llm_client, extract_token_usage


def json_to_mermaid(json_data: dict) -> str:
    """Convert graph JSON to Mermaid format"""
    lines = ["flowchart TD"]

    nodes = json_data.get("nodes", [])
    edges = json_data.get("edges", [])

    # Add all nodes
    for node in nodes:
        node_id = node.get("id", "").replace(":", "_").replace(".", "_")
        number = node.get("number", "")
        title = node.get("title", "")
        pages = node.get("appears_on_pages", [])

        # Format label
        label = f"{number} {title}".strip()
        if pages:
            page_str = f"(Pages: {', '.join(map(str, pages))})"
            label = f"{label}<br/>{page_str}"

        # Escape special characters
        label = label.replace('"', "'").replace("[", "(").replace("]", ")")

        lines.append(f'    {node_id}["{label}"]')

    # Add edges
    for edge in edges:
        from_id = edge.get("from", "").replace(":", "_").replace(".", "_")
        to_id = edge.get("to", "").replace(":", "_").replace(".", "_")
        edge_type = edge.get("type", "relates to")

        lines.append(f'    {from_id} -->|"{edge_type}"| {to_id}')

    return "\n".join(lines)


def generate_derived_graph(graph_type: str, input_json_path: Path, output_dir: Path,
                           prompt_path: Path, client, provider, model: str):
    """
    Generate a single derived graph.
    Returns (success: bool, token_usage: dict, node_count: int, edge_count: int)
    """
    try:
        # Load input JSON
        with open(input_json_path, "r", encoding="utf-8") as f:
            input_data = json.load(f)

        # Load prompt
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        # Prepare input for LLM
        user_message = f"{prompt_template}\n\nINPUT JSON:\n{json.dumps(input_data, indent=2)}"

        # Call LLM
        if provider == "anthropic":
            response = client.messages.create(
                model=model,
                max_tokens=16000,
                temperature=0,
                messages=[{"role": "user", "content": user_message}]
            )
            result_text = response.content[0].text.strip()
            token_usage = extract_token_usage(response, provider)
        elif provider == "openai":
            # Newer OpenAI models use max_completion_tokens instead of max_tokens
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an expert at knowledge graph transformation."},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0,
                    response_format={"type": "json_object"},
                    max_completion_tokens=16000
                )
            except Exception as e:
                # Fallback to max_tokens for older models
                if "max_completion_tokens" in str(e):
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are an expert at knowledge graph transformation."},
                            {"role": "user", "content": user_message}
                        ],
                        temperature=0,
                        response_format={"type": "json_object"},
                        max_tokens=16000
                    )
                else:
                    raise
            result_text = response.choices[0].message.content.strip()
            token_usage = extract_token_usage(response, provider)
        elif provider == "gemini":
            import google.generativeai as genai
            generation_config = {
                "temperature": 0,
                "max_output_tokens": 16000,
                "response_mime_type": "application/json"
            }
            response = client.generate_content(
                [{"role": "user", "parts": [user_message]}],
                generation_config=generation_config
            )
            result_text = response.text.strip()
            token_usage = extract_token_usage(response, provider)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Parse JSON
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()

        graph_data = json.loads(result_text)

        node_count = len(graph_data.get('nodes', []))
        edge_count = len(graph_data.get('edges', []))

        # Save JSON
        json_path = output_dir / "json" / f"{graph_type}.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2)

        # Convert to Mermaid and save
        mermaid_output = json_to_mermaid(graph_data)
        mermaid_path = output_dir / "mermaid" / f"{graph_type}.mermaid"
        mermaid_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write(mermaid_output)

        return True, token_usage, node_count, edge_count

    except Exception as e:
        print(f"Error generating {graph_type}: {e}")
        import traceback
        traceback.print_exc()
        return False, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}, 0, 0


def generate_all_derived_graphs(document_name: str = "Defence_Standard_00-056_Part_01.txt",
                               selected_types: list = None):
    """
    Generate derived graphs and return summary with token usage.

    Args:
        document_name: Name of the document to process
        selected_types: List of graph types to generate (e.g., ["index_file", "index_chapter"]).
                       If None, generates all graphs.
    """
    # Load config
    try:
        config = get_llm_config()
        client, provider = get_llm_client(config)
        model = config.get("model")
        print(f"Using LLM provider: {provider} with model: {model}")
    except Exception as e:
        return {
            "success": False,
            "error": f"Error loading config: {e}",
            "graphs": []
        }

    # Determine paths
    safe_doc_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in document_name])
    base_dir = Path(__file__).parent.parent.parent  # Go up to backend root
    output_dir = base_dir / "outputs" / safe_doc_name
    prompt_dir = base_dir / "inputs" / "promtps"

    master_json_path = output_dir / "json" / "master.json"

    # Check if master.json exists
    if not master_json_path.exists():
        return {
            "success": False,
            "error": f"master.json not found at {master_json_path}",
            "graphs": []
        }

    # Define all derived graphs to generate
    # Map of graph_type to config
    all_derived_graphs = {
        "index_file": {
            "type": "index_file",
            "name": "File Index",
            "description": "Document structure organized by files and sections",
            "input": master_json_path,
            "prompt": prompt_dir / "index_file.txt"
        },
        "index_chapter": {
            "type": "index_chapter",
            "name": "Chapter Index",
            "description": "High-level chapter overview with key relationships",
            "input": output_dir / "json" / "index_file.json",  # Uses file_index as input
            "prompt": prompt_dir / "index_chapter.txt"
        },
        "index_reference": {
            "type": "index_reference",
            "name": "Reference Index",
            "description": "External references and citations",
            "input": master_json_path,
            "prompt": prompt_dir / "index_reference.txt"
        },
        "index_section": {
            "type": "index_section",
            "name": "Section Index",
            "description": "Detailed section-level navigation for retrieval",
            "input": master_json_path,
            "prompt": prompt_dir / "index_section.txt"
        },
        "index_topic": {
            "type": "index_topic",
            "name": "Topic Index",
            "description": "Key concepts and topics across the document",
            "input": master_json_path,
            "prompt": prompt_dir / "index_topic.txt"
        }
    }

    # Filter graphs if specific types are requested
    if selected_types:
        derived_graphs = [all_derived_graphs[t] for t in selected_types if t in all_derived_graphs]
    else:
        derived_graphs = list(all_derived_graphs.values())

    if not derived_graphs:
        return {
            "success": False,
            "error": "No valid graph types selected",
            "graphs": []
        }

    results = []
    total_tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    for graph_spec in derived_graphs:
        graph_type = graph_spec["type"]
        graph_name = graph_spec["name"]
        input_path = graph_spec["input"]
        prompt_path = graph_spec["prompt"]

        print(f"\nGenerating {graph_name}...")

        # Check if input file exists (important for chapter_index which depends on file_index)
        if not input_path.exists():
            print(f"  Warning: Input file not found: {input_path}")
            results.append({
                "type": graph_type,
                "name": graph_name,
                "success": False,
                "error": "Input file not found",
                "nodes": 0,
                "edges": 0,
                "tokens": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            })
            continue

        success, token_usage, nodes, edges = generate_derived_graph(
            graph_type, input_path, output_dir, prompt_path, client, provider, model
        )

        # Accumulate token usage
        total_tokens["input_tokens"] += token_usage["input_tokens"]
        total_tokens["output_tokens"] += token_usage["output_tokens"]
        total_tokens["total_tokens"] += token_usage["total_tokens"]

        result = {
            "type": graph_type,
            "name": graph_name,
            "success": success,
            "nodes": nodes,
            "edges": edges,
            "tokens": token_usage
        }

        if success:
            print(f"  ✓ Generated {graph_name}: {nodes} nodes, {edges} edges")
            print(f"    Tokens: {token_usage['input_tokens']} in + {token_usage['output_tokens']} out = {token_usage['total_tokens']} total")
        else:
            result["error"] = "Generation failed"

        results.append(result)

    print(f"\n{'='*60}")
    print(f"Total token usage across all graphs:")
    print(f"  Input tokens:  {total_tokens['input_tokens']:,}")
    print(f"  Output tokens: {total_tokens['output_tokens']:,}")
    print(f"  Total tokens:  {total_tokens['total_tokens']:,}")
    print(f"{'='*60}\n")

    return {
        "success": True,
        "provider": provider,
        "graphs": results,
        "total_tokens": total_tokens,
        "document_name": document_name
    }


def get_available_derived_graphs():
    """
    Return list of all available derived graph types with metadata.
    """
    return [
        {
            "type": "index_file",
            "name": "File Index",
            "description": "Document structure organized by files and sections"
        },
        {
            "type": "index_chapter",
            "name": "Chapter Index",
            "description": "High-level chapter overview with key relationships"
        },
        {
            "type": "index_reference",
            "name": "Reference Index",
            "description": "External references and citations"
        },
        {
            "type": "index_section",
            "name": "Section Index",
            "description": "Detailed section-level navigation for retrieval"
        },
        {
            "type": "index_topic",
            "name": "Topic Index",
            "description": "Key concepts and topics across the document"
        }
    ]


if __name__ == "__main__":
    document_name = sys.argv[1] if len(sys.argv) > 1 else "Defence_Standard_00-056_Part_01.txt"
    result = generate_all_derived_graphs(document_name)

    if result["success"]:
        print("\n✓ All derived graphs generated successfully!")
        sys.exit(0)
    else:
        print(f"\n✗ Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)
