import json
from pathlib import Path
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder=".")

# Adjust path to map local repo structure
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "graph"

def aggregate_graph():
    """Reads all JSON graph fragments and concatenates them for web consumption."""
    nodes = []
    links = []

    for path in DATA_DIR.glob("*.json"):
        if path.name == "schema.json":
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                file_nodes = data.get("nodes", [])
                
                # Build master nodes list
                nodes.extend(file_nodes)
                
                # Build master edges list
                for n in file_nodes:
                    for e in n.get("edges", []):
                        links.append({
                            "source": n["id"],
                            "target": e["target"],
                            "relation": e["relation"]
                        })
        except Exception as e:
            print(f"Error reading {path.name}: {e}")

    return {"nodes": nodes, "links": links}

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/graph")
def api_graph():
    graph_data = aggregate_graph()
    return jsonify(graph_data)

if __name__ == "__main__":
    print("Starting Kripto Rehber Web Viewer at http://localhost:8081")
    app.run(host="0.0.0.0", port=8081)
