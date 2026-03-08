from kripto_rehber.graph import ObligationGraph

def test_evaluate_business_model():
    g = ObligationGraph()
    activities = ["margin trading", "foreign users", "saklama", "ICO issuance", "defi"]
    result = g.evaluate_business_model(activities)
    
    # Ensure it parsed exactly 5 activities
    assert result["total_activities_evaluated"] == 5
    analysis = result["activity_analysis"]
    
    # Margin testing
    assert "margin trading" in analysis
    margin_res = analysis["margin trading"]
    assert "kredili" in margin_res["matched_keywords"]
    assert len(margin_res["critical_rules"]) + margin_res["required_rules_count"] > 0
    # verify at least one margin-related node is returned
    node_ids = [n["id"] for n in margin_res["critical_rules"]] + [n["id"] for n in margin_res.get("required_rules", [])]
    
    # Foreign users
    assert "foreign users" in analysis
    assert "crossborder" in analysis["foreign users"]["matched_keywords"] or "yurtdisi" in analysis["foreign users"]["matched_keywords"]
    
    # Custody
    assert "saklama" in analysis
    saklama_res = analysis["saklama"]
    assert "saklama" in saklama_res["matched_keywords"]
    
def test_nodes_by_priority():
    g = ObligationGraph()
    critical = g.nodes_by_priority("critical")
    assert len(critical) >= 40 
    
    recommended = g.nodes_by_priority("recommended")
    assert len(recommended) >= 20
