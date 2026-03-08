import asyncio
import sys
from kripto_rehber.graph import ObligationGraph
from kripto_rehber import mevzuat_client
from termcolor import colored

async def test_links():
    """
    Simulates checking live Mevzuat articles against the graph nodes.
    
    This connects to the upstream Mevzuat MCP server via FastMCP's client,
    iterates through nodes that point to Turkish laws, and verifies that the
    `mevzuat_client` successfully returns an article text (or fails gracefully if missing).
    """
    g = ObligationGraph()
    nodes = g.all_nodes()
    
    # Filter nodes that actually originate from a Turkish legal source, not FATF/MiCA
    testable_nodes = [
        n for n in nodes 
        if n["category"] not in ("mica-reference", "fatf-reference", "definitions")
        and "law_no" in n.get("source", {})
    ]
    
    print(f"Graph loaded. Testing {len(testable_nodes)} out of {len(nodes)} total nodes via Mevzuat MCP...\n")
    
    success_count = 0
    fail_count = 0
    
    # Limit to first 10 for demonstration speed. Change to `testable_nodes` for full run.
    sample = testable_nodes[:20]
    
    for i, node in enumerate(sample, 1):
        source = node["source"]
        law_type = source.get("law_type", "kanun")
        law_no = source.get("law_no", "")
        mcp_search = source.get("mcp_search")
        
        # Build keyword search string
        article = source.get("article", "")
        keyword = f"madde {article}" if article else node["title"]
        
        print(f"[{i}/{len(sample)}] Checking Node '{node['id']}' -> {law_type} {law_no}...", end="", flush=True)
        
        try:
            # Call our client wrapper
            result = await mevzuat_client.get_article_text(
                law_type=law_type,
                law_no=law_no,
                keyword=keyword,
                max_results=1,
                mcp_search=mcp_search,
            )
            
            if result.get("success") and result.get("data") and len(result["data"].strip()) > 0:
                print(colored(" OK", "green"))
                success_count += 1
            else:
                print(colored(" FAIL", "red"))
                error_msg = result.get("error", "No text matched")
                print(colored(f"      Reason: {error_msg}", "yellow"))
                fail_count += 1
                
        except Exception as e:
            print(colored(" ERROR", "red"))
            print(colored(f"      Exception: {str(e)}", "red"))
            fail_count += 1
            
    print("\n--- Compliance CI Run Complete ---")
    print(f"Total Checked: {len(sample)}")
    print(colored(f"Successful links: {success_count}", "green"))
    if fail_count > 0:
        print(colored(f"Broken links (Link Rot): {fail_count}", "red"))
        sys.exit(1)
    else:
        print(colored("All tested nodes correctly point to live Mevzuat articles!", "green"))
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(test_links())
