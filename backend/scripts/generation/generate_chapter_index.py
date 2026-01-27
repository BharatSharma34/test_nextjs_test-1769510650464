#!/usr/bin/env python3
"""
Generate chapter index graph from file_index_graph.json
This creates a top-level chapter navigation by further collapsing the file index.
"""
import json
import sys
from pathlib import Path
from llm_config import get_llm_config, get_llm_client


def json_to_mermaid_index(json_data: dict) -> str:
    """Convert chapter index JSON to Mermaid format"""
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


def generate_chapter_index(document_name: str = "Defence_Standard_00-056_Part_01.txt"):
    """Generate chapter index graph from file_index_graph.json"""

    # Load config
    try:
        config = get_llm_config()
        client, provider = get_llm_client(config)
        print(f"Using LLM provider: {provider}")
    except Exception as e:
        print(f"Error loading config: {e}")
        return False

    # Determine paths
    safe_doc_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in document_name])
    base_dir = Path(__file__).parent.parent.parent  # Go up to backend root
    output_dir = base_dir / "outputs" / safe_doc_name

    file_index_json_path = output_dir / "json" / "file_index_graph.json"
    chapter_index_json_path = output_dir / "json" / "chapter_index_graph.json"
    chapter_index_mermaid_path = output_dir / "mermaid" / "chapter_index_graph.mermaid"

    # Check if file_index_graph.json exists
    if not file_index_json_path.exists():
        print(f"Error: file_index_graph.json not found at {file_index_json_path}")
        print("Please run generate_file_index.py first.")
        return False

    # Load file_index_graph.json
    print(f"Loading file_index_graph.json from {file_index_json_path}")
    with open(file_index_json_path, "r", encoding="utf-8") as f:
        file_index_data = json.load(f)

    print(f"File index has {len(file_index_data.get('nodes', []))} nodes and {len(file_index_data.get('edges', []))} edges")

    # Load prompt
    prompt_path = base_dir / "inputs" / "promtps" / "chapter_index_graph.txt"
    if not prompt_path.exists():
        print(f"Error: Prompt file not found at {prompt_path}")
        return False

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Prepare input for LLM
    user_message = f"{prompt_template}\n\nINPUT JSON:\n{json.dumps(file_index_data, indent=2)}"

    # Call LLM
    print(f"Sending request to {provider} API...")
    try:
        if provider == "anthropic":
            # Claude API
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )
            result_text = response.content[0].text.strip()
        else:
            # OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at knowledge graph transformation and document navigation systems."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=8000
            )
            result_text = response.choices[0].message.content.strip()

        print(f"Received response from {provider} ({len(result_text)} characters)")

        # Parse JSON (Claude may wrap in markdown, so strip that)
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()

        chapter_index_data = json.loads(result_text)

        print(f"Chapter index has {len(chapter_index_data.get('nodes', []))} nodes and {len(chapter_index_data.get('edges', []))} edges")

        # Save JSON
        chapter_index_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(chapter_index_json_path, "w", encoding="utf-8") as f:
            json.dump(chapter_index_data, f, indent=2)
        print(f"Saved chapter_index_graph.json to {chapter_index_json_path}")

        # Convert to Mermaid
        mermaid_output = json_to_mermaid_index(chapter_index_data)

        # Save Mermaid
        chapter_index_mermaid_path.parent.mkdir(parents=True, exist_ok=True)
        with open(chapter_index_mermaid_path, "w", encoding="utf-8") as f:
            f.write(mermaid_output)
        print(f"Saved chapter_index_graph.mermaid to {chapter_index_mermaid_path}")

        print("\n✓ Chapter index graph generated successfully!")
        return True

    except Exception as e:
        print(f"Error calling {provider} API: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    document_name = sys.argv[1] if len(sys.argv) > 1 else "Defence_Standard_00-056_Part_01.txt"
    success = generate_chapter_index(document_name)
    sys.exit(0 if success else 1)
