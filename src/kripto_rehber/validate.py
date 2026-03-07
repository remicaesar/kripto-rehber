"""
Graph validation: schema compliance, dangling edges, orphans, duplicates.

Run with: uv run python -m kripto_rehber.validate
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "graph"


def validate() -> bool:
    schema_path = DATA_DIR / "schema.json"
    with open(schema_path) as f:
        schema = json.load(f)

    all_nodes: list[dict] = []
    # Skip schema.json and non-graph files (licensing-paths.json has different structure)
    skip_files = {"schema.json", "licensing-paths.json"}
    files = sorted(p for p in DATA_DIR.glob("*.json") if p.name not in skip_files)

    if not files:
        print("ERROR: No graph JSON files found in data/graph/")
        return False

    errors: list[str] = []
    warnings: list[str] = []

    for path in files:
        with open(path) as f:
            data = json.load(f)

        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"[{path.name}] Schema violation: {e.message}")

        all_nodes.extend(data.get("nodes", []))

    node_ids = [n["id"] for n in all_nodes]
    node_set = set(node_ids)

    dupes = [nid for nid in node_ids if node_ids.count(nid) > 1]
    if dupes:
        errors.append(f"Duplicate IDs: {set(dupes)}")

    edge_count = 0
    for node in all_nodes:
        for edge in node.get("edges", []):
            edge_count += 1
            if edge["target"] not in node_set:
                errors.append(f"Dangling edge: {node['id']} --[{edge['relation']}]--> {edge['target']} (target not found)")

    connected = set()
    for node in all_nodes:
        if node.get("edges"):
            connected.add(node["id"])
            for edge in node["edges"]:
                connected.add(edge["target"])

    orphans = node_set - connected
    if orphans:
        warnings.append(f"Orphan nodes (no edges): {orphans}")

    for node in all_nodes:
        chain = set()
        current = node["id"]
        basis_map: dict[str, str | None] = {}
        for n in all_nodes:
            for e in n.get("edges", []):
                if e["relation"] == "legal_basis":
                    basis_map[n["id"]] = e["target"]

        while current in basis_map:
            if current in chain:
                errors.append(f"Circular legal_basis chain involving: {current}")
                break
            chain.add(current)
            current = basis_map[current]

    print(f"Files checked: {len(files)}")
    print(f"Total nodes:   {len(all_nodes)}")
    print(f"Total edges:   {edge_count}")
    print(f"Categories:    {len(set(n['category'] for n in all_nodes))}")
    print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
        print()

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠ {w}")
        print()

    if not errors and not warnings:
        print("✓ Graph is valid. No issues found.")
    elif not errors:
        print("✓ Graph is valid (with warnings).")
    else:
        print("✗ Graph has errors.")

    return len(errors) == 0


def main():
    ok = validate()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
