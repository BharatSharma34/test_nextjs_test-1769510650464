import json
import os
import re
from pathlib import Path

def aggregate_assets(doc_dir: str):
    root = Path(doc_dir)
    json_dir = root / "json"
    mermaid_dir = root / "mermaid"
    
    # helper for natural sorting
    def sort_key(f):
        nums = re.findall(r'\d+', f.name)
        return int(nums[0]) if nums else 0

    # 1. Aggregate JSON
    master_json = {
        "graph_intent": "hybrid_structure_reference",
        "nodes": [],
        "edges": []
    }
    json_files = sorted([f for f in json_dir.glob("page_*.json")], key=sort_key)
    seen_nodes = set()
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            for node in data.get("nodes", []):
                nid = node.get("canonical_id") or node.get("id")
                if nid not in seen_nodes:
                    master_json["nodes"].append(node)
                    seen_nodes.add(nid)
            master_json["edges"].extend(data.get("edges", []))
        except Exception as e:
            print(f"Error reading JSON {jf.name}: {e}")
    
    json_output = json_dir / "master.json"
    json_output.write_text(json.dumps(master_json, indent=2), encoding="utf-8")
    print(f"Master JSON aggregated: {len(master_json['nodes'])} nodes, {len(json_output.name)} total path")

    # 2. Aggregate Mermaid
    mermaid_files = sorted([f for f in mermaid_dir.glob("page_*.mermaid")], key=sort_key)
    mermaid_lines = ["flowchart TD"]
    for mf in mermaid_files:
        content = mf.read_text(encoding="utf-8").strip()
        # Remove any flowchart TD or graph TD headers from individual pages
        # (Individual pages need 'flowchart TD' for standalone viewing, but master needs only one)
        content = re.sub(r'^(flowchart|graph)\s+\w+\s*\n?', '', content, flags=re.IGNORECASE | re.MULTILINE)
        content = content.strip()
        if content:
            mermaid_lines.append(content)
    
    mermaid_output = mermaid_dir / "master.mermaid"
    mermaid_output.write_text("\n".join(mermaid_lines), encoding="utf-8")
    print(f"Master Mermaid aggregated from {len(mermaid_files)} files at {mermaid_output}")

if __name__ == "__main__":
    base_path = "/Users/jd/Development/Barkley/worsley-1769261842505/backend/outputs/Defence_Standard_00-056_Part_01_txt"
    aggregate_assets(base_path)
