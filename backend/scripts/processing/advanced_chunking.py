import os
import sys
import json
import asyncio
import re
import textwrap
import hashlib
from pathlib import Path
from typing import List, Dict, Any

# Add SDK path to sys.path
SDK_PATH = Path("/Users/jd/Development/Barkley/tapestry_sdk_python")
if str(SDK_PATH) not in sys.path:
    sys.path.append(str(SDK_PATH))

from .chunk_document import chunk_document_file
from llm_config import get_llm_config, get_llm_client

def generate_stable_id(doc_key: str, node: Dict[str, Any]) -> str:
    """Generates a stable, deterministic canonical ID: DOC:PATH~HASH8"""
    path = node.get("id", "unknown") # This is the semantic path/slug from LLM
    node_kind = node.get("kind", "node")
    title = node.get("title", "").strip().lower()
    page = node.get("page", 0)
    source_span = node.get("source_span", "").strip()
    
    # Hash input: doc_key|node_type|path|title_normalized|source_page|source_span
    hash_input = f"{doc_key}|{node_kind}|{path}|{title}|{page}|{source_span}"
    full_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    hash8 = full_hash[:8]
    
    # Canonical ID: DOC:PATH~HASH8
    # Ensure path doesn't contain forbidden chars for canonical form
    clean_path = re.sub(r'[^a-zA-Z0-9_:]', '_', path)
    return f"{doc_key}:{clean_path}~{hash8}"

def derive_render_id(canonical_id: str) -> str:
    """Derives a Mermaid-safe render_id from a canonical ID."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', canonical_id)

def wrap_label(text: str, width: int = 40) -> str:
    """Wraps text with <br/> tags for clean Mermaid rendering."""
    if not text:
        return ""
    # Ensure it's a string
    text_str = str(text)
    wrapped = textwrap.wrap(text_str, width=width, break_long_words=False)
    return "<br/>".join(wrapped)

def json_to_mermaid(json_data: Dict[str, Any], page_num: int, doc_key: str) -> str:
    """Converts the rich JSON graph to an optimized Mermaid subgraph snippet with Stable IDs.
    Note: Individual page files include 'flowchart TD' so they can be viewed standalone."""
    lines = ["flowchart TD", f"subgraph Page_{page_num} [Page {page_num}]"]
    
    nodes = json_data.get("nodes", [])
    edges = json_data.get("edges", [])
    
    # Mapping to keep track of canonical -> render associations on this page
    id_map = {}
    
    # Enrich nodes with Stable IDs
    for node in nodes:
        # If node already has a canonical form from previous steps, we might want to preserve it
        # but here we generate fresh stable IDs based on LLM semantic output
        canonical_id = generate_stable_id(doc_key, node)
        render_id = derive_render_id(canonical_id)
        id_map[node.get("id")] = (canonical_id, render_id)
        
        node["canonical_id"] = canonical_id
        node["render_id"] = render_id

    # Separate structure and references for binary grouping
    structure_nodes = [n for n in nodes if n.get("kind") != "reference"]
    reference_nodes = [n for n in nodes if n.get("kind") == "reference"]
    
    # Add structure nodes
    for node in structure_nodes:
        render_id = node["render_id"]
        num = node.get("number", "")
        title = node.get("title", "")
        
        raw_label = f"{num} {title}".strip()
        label = wrap_label(raw_label.replace("\"", "'").replace("[", "").replace("]", ""))
        lines.append(f"    {render_id}[\"{label}\"]")
    
    # Add references in their own subgraph
    if reference_nodes:
        lines.append(f"    subgraph Page_{page_num}_Refs [References]")
        lines.append("        direction LR")
        for node in reference_nodes:
            render_id = node["render_id"]
            title = node.get("title", "Reference")
            label = wrap_label(title.replace("\"", "'").replace("[", "").replace("]", ""))
            lines.append(f"        {render_id}[\"{label}\"]")
        lines.append("    end")
    
    # Add edges using derived ids
    for edge in edges:
        start_semantic = edge.get("from")
        end_semantic = edge.get("to")
        
        # We need to map LLM semantic IDs to our generated render IDs
        start_rid = id_map.get(start_semantic, (None, "unknown_start"))[1]
        end_rid = id_map.get(end_semantic, (None, "unknown_end"))[1]
        
        edge_type = edge.get("type", "relates to")
        lines.append(f"    {start_rid} -->|\"{edge_type}\"| {end_rid}")
        
    lines.append("end")
    return "\n".join(lines)

async def generate_page_graph_llm(
    page_text: str,
    page_num: int,
    filename: str,
    doc_key: str,
    prompt_template: str,
    client,
    provider: str,
    semaphore: asyncio.Semaphore,
    output_dir: Path
):
    async with semaphore:
        prompt = prompt_template.replace("{{pageNumber}}", str(page_num)).replace("{{filename}}", filename)
        
        system_prompt = (
            "You are an expert at extracting structured relationship data from document pages for a TrustGraph-Lite index.\n"
            "You must identify structural elements (clauses, sections) and external references.\n"
            "Output MUST be a single JSON object. Use discrete fields: id (semantic path), number, title, kind, source_span.\n"
            "Keep node labels textually faithful."
        )
        
        user_content = f"PROMPT TEMPLATE:\n{prompt}\n\nPAGE CONTENT:\n{page_text}"
        
        try:
            print(f"DEBUG: Processing page {page_num}...")

            if provider == "anthropic":
                # Claude API
                from anthropic import Anthropic
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    temperature=0,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_content}
                    ]
                )
                answer = response.content[0].text.strip()
            else:
                # OpenAI API
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0,
                    response_format={"type": "json_object"}
                )
                answer = response.choices[0].message.content.strip()
            
            json_dir = output_dir / "json"
            mermaid_dir = output_dir / "mermaid"
            json_dir.mkdir(exist_ok=True)
            mermaid_dir.mkdir(exist_ok=True)

            try:
                json_data = json.loads(answer)
                # Save rich JSON
                (json_dir / f"page_{page_num}.json").write_text(json.dumps(json_data, indent=2), encoding="utf-8")
                # Convert to rich Mermaid
                mermaid_snippet = json_to_mermaid(json_data, page_num, doc_key)
                (mermaid_dir / f"page_{page_num}.mermaid").write_text(mermaid_snippet, encoding="utf-8")
                
                return {"mermaid": mermaid_snippet, "json": json_data}
                
            except json.JSONDecodeError:
                error_msg = f"Error[JSON Parse Error for OpenAI response]"
                return {"mermaid": f"subgraph Page_{page_num} [Page {page_num}]\n    {error_msg}\nend", "json": {"error": error_msg}}
                
        except Exception as e:
            error_msg = f"Error[OpenAI Error: {str(e)}]"
            return {"mermaid": f"subgraph Page_{page_num} [Page {page_num}]\n    {error_msg}\nend", "json": {"error": error_msg}}

async def perform_advanced_chunking(input_path: str, prompt_path: str, document_name: str) -> str:
    try:
        config = get_llm_config()
        client, provider = get_llm_client(config, async_client=True)
    except Exception as e:
        return f"flowchart TD\n    Error[Config Error: {str(e)}]"

    semaphore = asyncio.Semaphore(5)
    
    # Doc key for ID generation
    doc_key = "".join([c if c.isalnum() else "_" for c in document_name.split(".")[0]]).upper()
    
    safe_doc_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in document_name])
    output_dir = Path(__file__).resolve().parent / "outputs" / safe_doc_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    regex_path = os.path.join(os.path.dirname(__file__), "inputs", "regex.txt")
    try:
        payload, _ = chunk_document_file(input_path, regex_path)
    except Exception as e:
        return f"flowchart TD\n    Error[Chunking Error: {str(e)}]"
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    tasks = []
    for page in payload["pages"]:
        tasks.append(generate_page_graph_llm(
            page["text"],
            page["page_number"],
            document_name,
            doc_key,
            prompt_template,
            client,
            provider,
            semaphore,
            output_dir
        ))
    
    results = await asyncio.gather(*tasks)
    
    master_mermaid_list = ["flowchart TD"]
    master_json = {
        "graph_intent": "hybrid_structure_reference",
        "nodes": [],
        "edges": []
    }

    seen_nodes = set()
    for res in results:
        # Strip 'flowchart TD' from individual pages when building master
        page_mermaid = res["mermaid"]
        if page_mermaid.startswith("flowchart TD"):
            page_mermaid = page_mermaid.replace("flowchart TD", "", 1).strip()
        master_mermaid_list.append(page_mermaid)
        page_json = res["json"]
        if "error" not in page_json:
            for node in page_json.get("nodes", []):
                nid = node.get("canonical_id") or node.get("id")
                if nid not in seen_nodes:
                    master_json["nodes"].append(node)
                    seen_nodes.add(nid)
            master_json["edges"].extend(page_json.get("edges", []))

    master_mermaid_text = "\n".join(master_mermaid_list)
    
    # Save master files in subfolders
    (output_dir / "mermaid" / "master.mermaid").write_text(master_mermaid_text, encoding="utf-8")
    (output_dir / "json" / "master.json").write_text(json.dumps(master_json, indent=2), encoding="utf-8")
    
    return {
        "mermaid": master_mermaid_text,
        "json": master_json
    }
