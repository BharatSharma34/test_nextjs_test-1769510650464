#!/usr/bin/env python3
"""
Script to concatenate individual page mermaid and JSON files into master files.
"""
import json
from pathlib import Path
import re


def natural_sort_key(filename):
    """Extract page number for natural sorting (page_1, page_2, ..., page_10, etc.)"""
    match = re.search(r'page_(\d+)', filename.stem)
    if match:
        return int(match.group(1))
    return 0


def create_master_mermaid(mermaid_dir: Path):
    """Concatenate all page mermaid files into master.mermaid"""
    mermaid_files = [f for f in mermaid_dir.iterdir()
                     if f.is_file() and f.stem.startswith('page_') and f.suffix == '.mermaid']

    # Sort files by page number
    mermaid_files.sort(key=natural_sort_key)

    print(f"Found {len(mermaid_files)} mermaid files to concatenate")

    # Build the master mermaid content
    master_content = ["flowchart TD"]

    for mermaid_file in mermaid_files:
        print(f"  Processing {mermaid_file.name}")
        content = mermaid_file.read_text(encoding='utf-8').strip()

        # Add the subgraph content (skip if it's empty or contains errors)
        if content and "Error" not in content and "error" not in content:
            master_content.append(content)

    # Write the master file
    master_path = mermaid_dir / "master.mermaid"
    master_path.write_text('\n'.join(master_content), encoding='utf-8')
    print(f"\nCreated master.mermaid with {len(mermaid_files)} pages")
    print(f"Output: {master_path}")
    return master_path


def create_master_json(json_dir: Path):
    """Merge all page JSON files into master.json"""
    json_files = [f for f in json_dir.iterdir()
                  if f.is_file() and f.stem.startswith('page_') and f.suffix == '.json']

    # Sort files by page number
    json_files.sort(key=natural_sort_key)

    print(f"\nFound {len(json_files)} JSON files to merge")

    # Initialize master structure
    master_data = {
        "graph_intent": "hybrid_structure_reference",
        "nodes": [],
        "edges": []
    }

    node_ids = set()  # Track unique nodes

    for json_file in json_files:
        print(f"  Processing {json_file.name}")
        try:
            data = json.loads(json_file.read_text(encoding='utf-8'))

            # Add nodes (avoiding duplicates)
            for node in data.get('nodes', []):
                if node['id'] not in node_ids:
                    master_data['nodes'].append(node)
                    node_ids.add(node['id'])

            # Add all edges
            master_data['edges'].extend(data.get('edges', []))

        except Exception as e:
            print(f"    Warning: Could not process {json_file.name}: {e}")

    # Write the master file
    master_path = json_dir / "master.json"
    master_path.write_text(json.dumps(master_data, indent=2), encoding='utf-8')
    print(f"\nCreated master.json with {len(master_data['nodes'])} nodes and {len(master_data['edges'])} edges")
    print(f"Output: {master_path}")
    return master_path


def main():
    # Get the base output directory
    base_dir = Path(__file__).parent.parent.parent / "outputs" / "Defence_Standard_00-056_Part_01_txt"

    if not base_dir.exists():
        print(f"Error: Output directory not found: {base_dir}")
        return

    mermaid_dir = base_dir / "mermaid"
    json_dir = base_dir / "json"

    print("=" * 60)
    print("Creating Master Files")
    print("=" * 60)

    if mermaid_dir.exists():
        create_master_mermaid(mermaid_dir)
    else:
        print(f"Warning: Mermaid directory not found: {mermaid_dir}")

    if json_dir.exists():
        create_master_json(json_dir)
    else:
        print(f"Warning: JSON directory not found: {json_dir}")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
