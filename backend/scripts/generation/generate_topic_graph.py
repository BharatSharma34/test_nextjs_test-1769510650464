#!/usr/bin/env python3
"""
Generate topic retrieval graph from master.json
Focuses on key topics and concepts for semantic search.
"""
import json
import sys
from pathlib import Path
from llm_config import get_llm_config, get_llm_client


def json_to_mermaid_topic(json_data: dict) -> str:
    """Convert topic graph JSON to Mermaid format"""
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


def generate_topic_graph(document_name: str = "Defence_Standard_00-056_Part_01.txt"):
    """Generate topic retrieval graph from master.json"""

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

    master_json_path = output_dir / "json" / "master.json"
    topic_json_path = output_dir / "json" / "topic_graph.json"
    topic_mermaid_path = output_dir / "mermaid" / "topic_graph.mermaid"

    # Check if master.json exists
    if not master_json_path.exists():
        print(f"Error: master.json not found at {master_json_path}")
        return False

    # Load master.json
    print(f"Loading master.json from {master_json_path}")
    with open(master_json_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    print(f"Master graph has {len(master_data.get('nodes', []))} nodes and {len(master_data.get('edges', []))} edges")

    # Load prompt
    prompt_path = base_dir / "inputs" / "promtps" / "topic_graph.txt"
    if not prompt_path.exists():
        print(f"Error: Prompt file not found at {prompt_path}")
        return False

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Prepare input for LLM
    user_message = f"{prompt_template}\n\nINPUT JSON:\n{json.dumps(master_data, indent=2)}"

    # Call LLM
    print(f"Sending request to {provider} API...")
    try:
        if provider == "anthropic":
            # Claude API
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
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
                        "content": "You are an expert at extracting key topics and concepts for semantic retrieval systems."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=16000
            )
            result_text = response.choices[0].message.content.strip()

        print(f"Received response from {provider} ({len(result_text)} characters)")

        # Parse JSON (Claude may wrap in markdown, so strip that)
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()

        topic_data = json.loads(result_text)

        print(f"Topic graph has {len(topic_data.get('nodes', []))} nodes and {len(topic_data.get('edges', []))} edges")

        # Save JSON
        topic_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(topic_json_path, "w", encoding="utf-8") as f:
            json.dump(topic_data, f, indent=2)
        print(f"Saved topic_graph.json to {topic_json_path}")

        # Convert to Mermaid
        mermaid_output = json_to_mermaid_topic(topic_data)

        # Save Mermaid
        topic_mermaid_path.parent.mkdir(parents=True, exist_ok=True)
        with open(topic_mermaid_path, "w", encoding="utf-8") as f:
            f.write(mermaid_output)
        print(f"Saved topic_graph.mermaid to {topic_mermaid_path}")

        print("\n✓ Topic graph generated successfully!")
        return True

    except Exception as e:
        print(f"Error calling {provider} API: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    document_name = sys.argv[1] if len(sys.argv) > 1 else "Defence_Standard_00-056_Part_01.txt"
    success = generate_topic_graph(document_name)
    sys.exit(0 if success else 1)
