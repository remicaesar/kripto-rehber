"""
Obligation graph: loading, traversal, and search.

The graph is stored as JSON and loaded into memory. Nodes are obligations or
legal provisions; edges encode cross-references (legal_basis, implements,
requires, triggers, defines, penalizes, tr_eu_equivalent, amends, references).
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "graph"

UPSTREAM_RELATIONS = {"legal_basis", "implements", "defines", "amends"}
DOWNSTREAM_RELATIONS = {"requires", "triggers", "penalizes", "references"}
EQUIVALENCE_RELATIONS = {"tr_eu_equivalent"}


class ObligationGraph:
    """In-memory obligation graph with traversal and search."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self._nodes: dict[str, dict] = {}
        self._reverse: dict[str, list[tuple[str, str, Optional[str]]]] = {}
        self._data_dir = data_dir
        self._load()

    def _load(self) -> None:
        self._nodes.clear()
        self._reverse.clear()

        for path in sorted(self._data_dir.glob("*.json")):
            if path.name == "schema.json":
                continue
            with open(path) as f:
                data = json.load(f)
            for node in data.get("nodes", []):
                nid = node["id"]
                self._nodes[nid] = node
                for edge in node.get("edges", []):
                    target = edge["target"]
                    rel = edge["relation"]
                    note = edge.get("note")
                    self._reverse.setdefault(target, []).append((nid, rel, note))

    def reload(self) -> None:
        self._load()

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(n.get("edges", [])) for n in self._nodes.values())

    def get_node(self, node_id: str) -> Optional[dict]:
        return self._nodes.get(node_id)

    def all_nodes(self) -> list[dict]:
        return list(self._nodes.values())

    def categories(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for n in self._nodes.values():
            cat = n["category"]
            counts[cat] = counts.get(cat, 0) + 1
        return dict(sorted(counts.items()))

    def nodes_by_category(self, category: str) -> list[dict]:
        return [n for n in self._nodes.values() if n["category"] == category]

    def search(self, query: str) -> list[dict]:
        """Case-insensitive keyword search across id, title, description, and key_values."""
        q = query.lower()
        results = []
        for n in self._nodes.values():
            haystack = " ".join([
                n["id"],
                n["title"],
                n["description"],
                " ".join(str(v) for v in n.get("key_values", {}).values()),
            ]).lower()
            if q in haystack:
                results.append(n)
        return results

    def trace_upstream(self, node_id: str, max_depth: int = 10) -> list[dict]:
        """BFS upstream: follow legal_basis / implements / defines edges backward."""
        return self._bfs(node_id, direction="upstream", max_depth=max_depth)

    def trace_downstream(self, node_id: str, max_depth: int = 10) -> list[dict]:
        """BFS downstream: follow requires / triggers / penalizes edges forward."""
        return self._bfs(node_id, direction="downstream", max_depth=max_depth)

    def trace_full(self, node_id: str, max_depth: int = 10) -> dict:
        """Full trace: upstream + downstream + equivalences from a node."""
        node = self._nodes.get(node_id)
        if not node:
            return {"error": f"Node '{node_id}' not found"}

        return {
            "node": _summarize(node),
            "upstream": self.trace_upstream(node_id, max_depth),
            "downstream": self.trace_downstream(node_id, max_depth),
            "equivalences": self._equivalences(node_id),
        }

    def impact_analysis(self, law_no: str) -> dict:
        """Find all nodes sourced from a law and their downstream blast radius."""
        source_nodes = [
            n for n in self._nodes.values()
            if n["source"].get("law_no") == law_no
        ]
        if not source_nodes:
            return {"error": f"No nodes found with source law_no='{law_no}'"}

        affected: dict[str, dict] = {}
        for sn in source_nodes:
            affected[sn["id"]] = _summarize(sn)
            for item in self.trace_downstream(sn["id"]):
                affected[item["id"]] = item

        by_category: dict[str, list[dict]] = {}
        for item in affected.values():
            cat = item["category"]
            by_category.setdefault(cat, []).append(item)

        return {
            "law_no": law_no,
            "source_nodes": [_summarize(n) for n in source_nodes],
            "total_affected": len(affected),
            "by_category": by_category,
        }

    def compare_tr_mica(self, category: Optional[str] = None) -> dict:
        """Build TR ↔ MiCA comparison for a category (or all)."""
        pairs: list[dict] = []
        tr_only: list[dict] = []

        for n in self._nodes.values():
            if n["category"] == "mica-reference":
                continue
            if category and n["category"] != category:
                continue

            mica_edges = [
                e for e in n.get("edges", [])
                if e["relation"] == "tr_eu_equivalent"
            ]
            if mica_edges:
                for e in mica_edges:
                    mica_node = self._nodes.get(e["target"])
                    pairs.append({
                        "tr": _summarize(n),
                        "mica": _summarize(mica_node) if mica_node else {"id": e["target"], "note": "node not found"},
                    })
            else:
                tr_only.append(_summarize(n))

        mica_with_tr = {e["target"] for n in self._nodes.values() for e in n.get("edges", []) if e["relation"] == "tr_eu_equivalent"}
        mica_only = [
            _summarize(n) for n in self._nodes.values()
            if n["category"] == "mica-reference" and n["id"] not in mica_with_tr
        ]

        return {
            "category": category or "all",
            "matched_pairs": pairs,
            "tr_only": tr_only,
            "mica_only": mica_only,
        }

    def stats(self) -> dict:
        """Graph health overview."""
        edge_types: dict[str, int] = {}
        connection_counts: dict[str, int] = {}

        for n in self._nodes.values():
            nid = n["id"]
            outgoing = len(n.get("edges", []))
            incoming = len(self._reverse.get(nid, []))
            connection_counts[nid] = outgoing + incoming
            for e in n.get("edges", []):
                rel = e["relation"]
                edge_types[rel] = edge_types.get(rel, 0) + 1

        top_connected = sorted(connection_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        orphans = [nid for nid, count in connection_counts.items() if count == 0]
        leaves = [
            nid for nid, n in self._nodes.items()
            if not any(
                e["relation"] in DOWNSTREAM_RELATIONS
                for e in n.get("edges", [])
            ) and nid not in orphans
        ]
        roots = [
            nid for nid in self._nodes
            if not any(
                e["relation"] in UPSTREAM_RELATIONS
                for e in self._nodes[nid].get("edges", [])
            ) and nid not in orphans
        ]

        return {
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "categories": self.categories(),
            "edge_types": dict(sorted(edge_types.items())),
            "top_connected": [{"id": nid, "connections": c} for nid, c in top_connected],
            "orphan_nodes": orphans,
            "leaf_nodes": leaves,
            "root_nodes": roots,
        }

    # -- Sprint 4/5: Actionable compliance tools --

    _PRIORITY_ORDER = {"critical": 0, "required": 1, "recommended": 2}

    _SERVICE_ALIASES: dict[str, list[str]] = {
        "platform": ["platform", "alim satim"],
        "saklama": ["saklama", "custody"],
        "transfer": ["transfer"],
    }

    def _match_service(self, service_type: str) -> Optional[str]:
        st = service_type.lower()
        for alias, keywords in self._SERVICE_ALIASES.items():
            if any(k in st for k in [alias] + keywords):
                return alias
        return None

    def compliance_checklist(self, service_type: str) -> dict:
        """Obligations for a service type, grouped by category with priority summary."""
        matched = self._match_service(service_type)

        universal_categories = {
            "licensing", "aml", "kyc", "travel-rule", "reporting",
            "governance", "penalties", "tax", "technical",
            "consumer-protection", "transition",
        }

        relevant: list[dict] = []
        for n in self._nodes.values():
            cat = n["category"]
            if cat in universal_categories:
                relevant.append(n)
            elif cat == "capital":
                if not matched:
                    relevant.append(n)
                else:
                    desc = (n["description"] + " " + n["title"] + " "
                            + n.get("key_values", {}).get("service_type", "")).lower()
                    is_general = not any(
                        k in desc for kws in self._SERVICE_ALIASES.values() for k in kws
                    )
                    is_match = any(k in desc for k in self._SERVICE_ALIASES.get(matched, []))
                    if is_general or is_match:
                        relevant.append(n)
            elif cat == "custody":
                if not matched or matched == "saklama":
                    relevant.append(n)

        # Build summary per category: critical items + counts
        category_order = [
            "licensing", "capital", "governance", "aml", "kyc",
            "travel-rule", "custody", "technical", "reporting",
            "consumer-protection", "tax", "penalties", "transition",
        ]
        checklist: dict[str, dict] = {}
        for n in relevant:
            cat = n["category"]
            if cat not in checklist:
                checklist[cat] = {"critical": [], "required_count": 0, "recommended_count": 0}
            pri = n.get("priority", "required")
            if pri == "critical":
                checklist[cat]["critical"].append(_summarize(n))
            elif pri == "required":
                checklist[cat]["required_count"] += 1
            else:
                checklist[cat]["recommended_count"] += 1

        sorted_checklist: dict[str, dict] = {}
        for cat in category_order:
            if cat in checklist:
                sorted_checklist[cat] = checklist[cat]
        for cat in checklist:
            if cat not in sorted_checklist:
                sorted_checklist[cat] = checklist[cat]

        total_critical = sum(len(v["critical"]) for v in checklist.values())

        return {
            "service_type": service_type,
            "matched_as": matched or "genel",
            "total_obligations": len(relevant),
            "total_critical": total_critical,
            "categories": len(sorted_checklist),
            "checklist": sorted_checklist,
        }

    def deadlines(self) -> dict:
        """Time-sensitive obligations grouped by deadline_type."""
        # Keys that are clearly time-related
        time_keys = {
            "deadline", "frequency", "retention_period", "update_frequency",
            "compliance_period", "period", "max_suspension",
        }
        # Keys that are NOT deadlines (penalties, requirements)
        excluded_keys = {
            "imprisonment", "judicial_fine", "prison", "ban_period",
            "min_fine", "max_fine", "min", "max",
            "obligations", "requirements", "requirement", "elements",
            "additions", "deductions", "calculation", "scope",
            "permit_types", "regulator", "payment", "protection",
            "alternatives", "mechanism", "stages", "display", "content",
            "prohibited", "required", "role", "risks", "locations",
            "measures", "action_on_mismatch", "overrides", "system",
            "triggers", "applicability", "threshold", "lists", "timing",
            "self_dealing", "irreversibility_disclosure", "options",
            "exemption", "allowed", "service_type", "submit_to",
            "format", "report_to", "basis", "information",
            "notification", "cost", "framework", "added_by",
            "gdpr_compliance", "penalty_for_delay",
        }

        entries: list[dict] = []
        for n in self._nodes.values():
            kv = n.get("key_values", {})
            has_deadline_type = "deadline_type" in kv
            time_entries = {}
            for k, v in kv.items():
                if k == "deadline_type":
                    continue
                k_lower = k.lower()
                # If node has explicit deadline_type, include all non-excluded kv
                if has_deadline_type and k_lower not in excluded_keys:
                    time_entries[k] = v
                    continue
                # Otherwise use key matching
                if k_lower in time_keys:
                    time_entries[k] = v
                elif k_lower in excluded_keys:
                    continue
                elif any(tw in k_lower for tw in ["deadline", "frequency", "retention"]):
                    time_entries[k] = v
            if time_entries:
                entries.append({
                    "id": n["id"],
                    "category": n["category"],
                    "title": n["title"],
                    "priority": n.get("priority", "required"),
                    "deadline_type": kv.get("deadline_type"),
                    "time_values": time_entries,
                    "source_law": n["source"].get("law_no", ""),
                })

        # Group using deadline_type metadata first, fallback to heuristic
        buckets: dict[str, list[dict]] = {
            "notification": [],
            "reporting": [],
            "transition": [],
            "retention": [],
            "customer_right": [],
        }

        for e in entries:
            dt = e.get("deadline_type")
            if dt and dt in buckets:
                buckets[dt].append(e)
            else:
                # Fallback heuristic for nodes without deadline_type
                tv = " ".join(e["time_values"].values()).lower()
                if e["category"] == "transition":
                    buckets["transition"].append(e)
                elif "derhal" in tv or "aninda" in tv:
                    buckets["notification"].append(e)
                elif "retention" in " ".join(e["time_values"].keys()).lower() or "saklama suresi" in tv:
                    buckets["retention"].append(e)
                elif any(w in tv for w in ["aylik", "ucaylik", "yillik", "haftalik"]):
                    buckets["reporting"].append(e)
                else:
                    buckets["reporting"].append(e)

        # Sort each bucket: critical first
        for items in buckets.values():
            items.sort(key=lambda x: self._PRIORITY_ORDER.get(x.get("priority", "required"), 1))

        return {
            "total_time_sensitive": len(entries),
            "notification": buckets["notification"],
            "reporting": buckets["reporting"],
            "transition": buckets["transition"],
            "retention": buckets["retention"],
            "customer_right": buckets["customer_right"],
        }

    def licensing_roadmap(self, service_type: str) -> dict:
        """Curated step-by-step licensing roadmap from licensing-paths.json."""
        matched = self._match_service(service_type) or service_type.lower()

        # Load curated paths
        paths_file = self._data_dir / "licensing-paths.json"
        if paths_file.exists():
            with open(paths_file) as f:
                paths_data = json.load(f)
            path = paths_data.get("paths", {}).get(matched)
            if path:
                # Enrich steps with node details
                enriched_steps = []
                for step in path["steps"]:
                    node = self._nodes.get(step["node_id"])
                    enriched = {
                        "seq": step["seq"],
                        "phase": step["phase"],
                        "title": step["title"],
                        "blocker": step["blocker"],
                        "node_id": step["node_id"],
                    }
                    if node:
                        enriched["description"] = node["description"]
                        enriched["key_values"] = node.get("key_values", {})
                    enriched_steps.append(enriched)

                return {
                    "service_type": service_type,
                    "capital_required": path["capital_required"],
                    "total_steps": len(enriched_steps),
                    "blocker_steps": sum(1 for s in enriched_steps if s["blocker"]),
                    "steps": enriched_steps,
                }

        # Fallback: no curated path found
        return {
            "service_type": service_type,
            "capital_required": "bilinmiyor",
            "total_steps": 0,
            "blocker_steps": 0,
            "steps": [],
            "note": f"No curated licensing path for '{service_type}'",
        }

    # -- internal helpers --

    def _bfs(self, start_id: str, direction: str, max_depth: int) -> list[dict]:
        if start_id not in self._nodes:
            return []

        visited: set[str] = set()
        queue: deque[tuple[str, int, str]] = deque()
        queue.append((start_id, 0, ""))
        results: list[dict] = []

        while queue:
            nid, depth, via_relation = queue.popleft()
            if nid in visited or depth > max_depth:
                continue
            visited.add(nid)

            node = self._nodes.get(nid)
            if not node:
                continue

            if nid != start_id:
                item = _summarize(node)
                item["depth"] = depth
                item["via_relation"] = via_relation
                results.append(item)

            if direction == "upstream":
                for src_id, rel, _note in self._reverse.get(nid, []):
                    if rel in UPSTREAM_RELATIONS:
                        queue.append((src_id, depth + 1, rel))
            elif direction == "downstream":
                for edge in node.get("edges", []):
                    if edge["relation"] in DOWNSTREAM_RELATIONS:
                        queue.append((edge["target"], depth + 1, edge["relation"]))

        return results

    def _equivalences(self, node_id: str) -> list[dict]:
        node = self._nodes.get(node_id)
        if not node:
            return []

        results = []
        for edge in node.get("edges", []):
            if edge["relation"] in EQUIVALENCE_RELATIONS:
                target = self._nodes.get(edge["target"])
                if target:
                    results.append(_summarize(target))

        for src_id, rel, _note in self._reverse.get(node_id, []):
            if rel in EQUIVALENCE_RELATIONS:
                src = self._nodes.get(src_id)
                if src:
                    results.append(_summarize(src))

        return results


def _summarize(node: dict) -> dict:
    """Compact representation of a node for API responses."""
    return {
        "id": node["id"],
        "category": node["category"],
        "title": node["title"],
        "description": node["description"],
        "priority": node.get("priority", "required"),
        "source_law": node["source"].get("law_no", ""),
        "source_article": node["source"].get("article", ""),
        "key_values": node.get("key_values", {}),
    }
