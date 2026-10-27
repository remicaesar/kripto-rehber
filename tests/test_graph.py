"""Tests for the obligation graph engine."""

from kripto_rehber.graph import ObligationGraph


def test_load():
    g = ObligationGraph()
    assert g.node_count > 0
    assert g.edge_count > 0


def test_categories():
    g = ObligationGraph()
    cats = g.categories()
    assert "aml" in cats
    assert "licensing" in cats
    assert "kyc" in cats


def test_get_node():
    g = ObligationGraph()
    node = g.get_node("def-kvhs")
    assert node is not None
    assert node["category"] == "definitions"


def test_get_node_missing():
    g = ObligationGraph()
    assert g.get_node("nonexistent-node") is None


def test_nodes_by_category():
    g = ObligationGraph()
    aml = g.nodes_by_category("aml")
    assert len(aml) > 0
    assert all(n["category"] == "aml" for n in aml)


def test_search():
    g = ObligationGraph()
    results = g.search("kimlik tespiti")
    assert len(results) > 0


def test_search_no_results():
    g = ObligationGraph()
    results = g.search("xyznonexistent123")
    assert len(results) == 0


def test_trace_upstream():
    g = ObligationGraph()
    upstream = g.trace_upstream("kyc-identity-threshold")
    ids = [n["id"] for n in upstream]
    assert "aml-masak-regulation" in ids or "aml-law-5549-base" in ids


def test_trace_downstream():
    g = ObligationGraph()
    downstream = g.trace_downstream("licensing-spk-permit")
    ids = [n["id"] for n in downstream]
    assert len(ids) > 0


def test_trace_full():
    g = ObligationGraph()
    result = g.trace_full("kyc-identity-threshold")
    assert "node" in result
    assert "upstream" in result
    assert "downstream" in result
    assert "equivalences" in result


def test_trace_full_missing():
    g = ObligationGraph()
    result = g.trace_full("nonexistent")
    assert "error" in result


def test_impact_analysis():
    g = ObligationGraph()
    result = g.impact_analysis("6362")
    assert result["total_affected"] > 0
    assert len(result["source_nodes"]) > 0


def test_impact_analysis_missing():
    g = ObligationGraph()
    result = g.impact_analysis("99999")
    assert "error" in result


def test_compare_tr_mica():
    g = ObligationGraph()
    result = g.compare_tr_mica()
    assert "matched_pairs" in result
    assert len(result["matched_pairs"]) > 0


def test_compare_tr_mica_category():
    g = ObligationGraph()
    result = g.compare_tr_mica("kyc")
    assert result["category"] == "kyc"


def test_stats():
    g = ObligationGraph()
    s = g.stats()
    assert s["total_nodes"] > 0
    assert s["total_edges"] > 0
    assert "categories" in s
    assert "top_connected" in s


def test_governance_category():
    g = ObligationGraph()
    gov = g.nodes_by_category("governance")
    assert len(gov) >= 4
    ids = [n["id"] for n in gov]
    assert "governance-compliance-officer" in ids
    assert "governance-board-oversight" in ids


def test_tax_category():
    g = ObligationGraph()
    tax = g.nodes_by_category("tax")
    assert len(tax) >= 4
    ids = [n["id"] for n in tax]
    assert "tax-income-capital-gains" in ids
    assert "tax-corporate" in ids


def test_fatf_reference_category():
    g = ObligationGraph()
    fatf = g.nodes_by_category("fatf-reference")
    assert len(fatf) >= 2
    ids = [n["id"] for n in fatf]
    assert "fatf-r15" in ids
    assert "fatf-r16" in ids


def test_mica_licensing_comparison():
    g = ObligationGraph()
    result = g.compare_tr_mica("licensing")
    assert len(result["matched_pairs"]) > 0


def test_impact_analysis_5549():
    g = ObligationGraph()
    result = g.impact_analysis("5549")
    assert result["total_affected"] > 5
    cats = list(result["by_category"].keys())
    assert "penalties" in cats or "aml" in cats


def test_mcp_search_params_present():
    """Verify key nodes have mcp_search params for Mevzuat MCP integration."""
    g = ObligationGraph()
    nodes_with_mcp = [
        n for n in g.all_nodes()
        if n["source"].get("mcp_search")
    ]
    assert len(nodes_with_mcp) >= 8


def test_graph_size_sprint1():
    """Sprint 1 target: 50+ nodes, 100+ edges."""
    g = ObligationGraph()
    assert g.node_count >= 50
    assert g.edge_count >= 100


def test_graph_size_sprint3():
    """Sprint 3 target: 200+ nodes, 400+ edges."""
    g = ObligationGraph()
    assert g.node_count >= 200
    assert g.edge_count >= 400


def test_teblig_b1_nodes():
    """Teblig III-35/B.1 operational nodes added in Sprint 3."""
    g = ObligationGraph()
    # Licensing
    assert g.get_node("licensing-basvuru-belgeleri") is not None
    assert g.get_node("licensing-faaliyet-izni-iptali") is not None
    assert g.get_node("licensing-beyaz-liste") is not None
    # Governance
    assert g.get_node("governance-yk-bagimsiz-uye") is not None
    assert g.get_node("governance-genel-mudur") is not None
    assert g.get_node("governance-ic-kontrol") is not None
    assert g.get_node("governance-risk-yonetimi") is not None
    # Technical
    assert g.get_node("technical-bilgi-sistemleri") is not None
    assert g.get_node("technical-siber-guvenlik") is not None
    assert g.get_node("technical-felaket-kurtarma") is not None
    assert g.get_node("technical-kripto-anahtar-yonetimi") is not None
    # Custody
    assert g.get_node("custody-varlik-ayristirma") is not None
    assert g.get_node("custody-soguk-cuzdan-orani") is not None


def test_teblig_b2_capital_nodes():
    """Teblig III-35/B.2 capital adequacy nodes."""
    g = ObligationGraph()
    assert g.get_node("capital-asgari-platform") is not None
    assert g.get_node("capital-asgari-saklama") is not None
    assert g.get_node("capital-asgari-transfer") is not None
    assert g.get_node("capital-sermaye-yeterlilik-orani") is not None
    assert g.get_node("capital-stres-testi") is not None
    # Check key values
    platform = g.get_node("capital-asgari-platform")
    assert platform["key_values"]["min_capital"] == "150.000.000 TL"


def test_kanun_6362_penalty_nodes():
    """Kanun 6362 articles 99/A, 109/A, 110/A penalty nodes."""
    g = ObligationGraph()
    assert g.get_node("law-6362-art99a-idari-para") is not None
    assert g.get_node("law-6362-art109a-izinsiz-faaliyet") is not None
    assert g.get_node("law-6362-art110a-zimmet") is not None
    assert g.get_node("law-6362-art99b-dolandiricilik") is not None
    # Verify corrected article numbers
    izinsiz = g.get_node("law-6362-art109a-izinsiz-faaliyet")
    assert izinsiz["source"]["article"] == "109/A"
    zimmet = g.get_node("law-6362-art110a-zimmet")
    assert zimmet["source"]["article"] == "110/A"
    assert "5-12 yil" in zimmet["key_values"]["imprisonment"]


def test_article_35b_35c_fix():
    """Verify 35/A was corrected to 35/B and 35/C."""
    g = ObligationGraph()
    kvhs = g.get_node("def-kvhs")
    assert kvhs["source"]["article"] == "35/B"
    services = g.get_node("licensing-permitted-services")
    assert services["source"]["article"] == "35/C"


def test_technical_category_expanded():
    """Technical category should have multiple nodes after Sprint 3."""
    g = ObligationGraph()
    tech = g.nodes_by_category("technical")
    assert len(tech) >= 8


def test_reporting_category_expanded():
    """Reporting category should be well-populated after Sprint 3."""
    g = ObligationGraph()
    reporting = g.nodes_by_category("reporting")
    assert len(reporting) >= 8


def test_consumer_protection_category():
    """Consumer protection nodes added in Sprint 3."""
    g = ObligationGraph()
    cp = g.nodes_by_category("consumer-protection")
    assert len(cp) >= 8
    assert g.get_node("consumer-risk-uyarisi") is not None
    assert g.get_node("consumer-varlik-guvencesi") is not None
    assert g.get_node("consumer-tazmin-fonu") is not None
    assert g.get_node("consumer-cayma-hakki") is not None


def test_transition_category():
    """Transition provision nodes for Kanun 7518."""
    g = ObligationGraph()
    tr = g.nodes_by_category("transition")
    assert len(tr) >= 5
    gecis = g.get_node("transition-gecis-suresi")
    assert gecis is not None
    assert gecis["key_values"]["deadline"] == "1 yil"
    assert g.get_node("transition-faaliyet-durdurma") is not None
    assert g.get_node("transition-masak-uyum") is not None


def test_crossborder_nodes():
    """Cross-border licensing nodes."""
    g = ObligationGraph()
    assert g.get_node("crossborder-yurtdisi-kvhs") is not None
    assert g.get_node("crossborder-erisim-engeli") is not None


# -- Sprint 4/5: Actionable compliance tools with priority --


def test_compliance_checklist_platform():
    g = ObligationGraph()
    result = g.compliance_checklist("platform")
    assert result["matched_as"] == "platform"
    assert result["total_obligations"] > 20
    assert result["total_critical"] > 10
    assert "licensing" in result["checklist"]
    assert "aml" in result["checklist"]
    assert "governance" in result["checklist"]
    # Checklist should have critical items list + counts
    licensing = result["checklist"]["licensing"]
    assert "critical" in licensing
    assert "required_count" in licensing
    assert len(licensing["critical"]) > 0


def test_compliance_checklist_saklama():
    g = ObligationGraph()
    result = g.compliance_checklist("saklama")
    assert result["matched_as"] == "saklama"
    assert "custody" in result["checklist"]


def test_compliance_checklist_transfer():
    g = ObligationGraph()
    result = g.compliance_checklist("transfer")
    assert result["matched_as"] == "transfer"
    assert result["total_obligations"] > 10


def test_compliance_checklist_unknown_service():
    g = ObligationGraph()
    result = g.compliance_checklist("danismanlik")
    assert result["matched_as"] == "genel"
    assert result["total_obligations"] > 0


def test_deadlines_uses_deadline_type():
    """Deadlines should use deadline_type metadata for clean bucketing."""
    g = ObligationGraph()
    result = g.deadlines()
    assert result["total_time_sensitive"] > 10
    # New bucket names
    assert "notification" in result
    assert "reporting" in result
    assert "transition" in result
    assert "retention" in result
    assert "customer_right" in result
    # Transition should have transition-tagged nodes
    assert len(result["transition"]) > 0
    # Customer rights should not be in reporting
    customer_ids = {e["id"] for e in result["customer_right"]}
    reporting_ids = {e["id"] for e in result["reporting"]}
    assert "consumer-cayma-hakki" in customer_ids
    assert "consumer-cayma-hakki" not in reporting_ids


def test_deadlines_notification_bucket():
    g = ObligationGraph()
    result = g.deadlines()
    notif_ids = {e["id"] for e in result["notification"]}
    assert "capital-sinir-asimi-bildirimi" in notif_ids
    assert "kvkk-veri-ihlali-bildirim" in notif_ids


def test_deadlines_retention_bucket():
    g = ObligationGraph()
    result = g.deadlines()
    ret_ids = {e["id"] for e in result["retention"]}
    assert "aml-record-keeping" in ret_ids
    assert "reporting-kayit-saklama" in ret_ids


def test_deadlines_priority_ordering():
    """Critical items should come first in each bucket."""
    g = ObligationGraph()
    result = g.deadlines()
    for bucket in ["notification", "reporting", "transition"]:
        items = result[bucket]
        if len(items) >= 2:
            priorities = [e.get("priority", "required") for e in items]
            # Critical should not appear after required/recommended
            seen_non_critical = False
            for p in priorities:
                if p != "critical":
                    seen_non_critical = True
                if p == "critical" and seen_non_critical:
                    assert False, f"Critical item after non-critical in {bucket}"


def test_licensing_roadmap_platform():
    g = ObligationGraph()
    result = g.licensing_roadmap("platform")
    assert result["capital_required"] == "150.000.000 TL"
    assert result["total_steps"] == 15
    assert result["blocker_steps"] >= 12
    # Steps should be flat list with seq numbers
    assert result["steps"][0]["seq"] == 1
    assert result["steps"][-1]["seq"] == 15
    # First step is company formation
    assert result["steps"][0]["phase"] == "kurulus"
    # Last step is SPK permit
    assert result["steps"][-1]["node_id"] == "licensing-spk-permit"


def test_licensing_roadmap_saklama():
    g = ObligationGraph()
    result = g.licensing_roadmap("saklama")
    assert result["capital_required"] == "500.000.000 TL"
    assert result["total_steps"] == 16
    # Should include custody-specific steps
    node_ids = [s["node_id"] for s in result["steps"]]
    assert "custody-cold-hot-wallet" in node_ids
    assert "custody-soguk-cuzdan-orani" in node_ids


def test_licensing_roadmap_transfer():
    g = ObligationGraph()
    result = g.licensing_roadmap("transfer")
    assert result["capital_required"] == "10.000.000 TL"
    assert result["total_steps"] == 11
    # Should include travel rule
    node_ids = [s["node_id"] for s in result["steps"]]
    assert "travel-rule-obligations" in node_ids


def test_licensing_roadmap_enriched():
    """Roadmap steps should include node descriptions and key_values."""
    g = ObligationGraph()
    result = g.licensing_roadmap("platform")
    capital_step = [s for s in result["steps"] if s["node_id"] == "capital-asgari-platform"][0]
    assert "description" in capital_step
    assert "key_values" in capital_step
    assert capital_step["key_values"]["min_capital"] == "150.000.000 TL"


def test_licensing_roadmap_unknown():
    g = ObligationGraph()
    result = g.licensing_roadmap("danismanlik")
    assert result["total_steps"] == 0
    assert "note" in result


# -- Sprint 5: Priority metadata --


def test_priority_field_exists():
    """All nodes should have a priority field."""
    g = ObligationGraph()
    for n in g.all_nodes():
        assert "priority" in n, f"Node {n['id']} missing priority"
        assert n["priority"] in ("critical", "required", "recommended")


def test_priority_distribution():
    """Reasonable distribution: ~50 critical, ~35 recommended, rest required."""
    g = ObligationGraph()
    counts = {"critical": 0, "required": 0, "recommended": 0}
    for n in g.all_nodes():
        counts[n["priority"]] += 1
    assert counts["critical"] >= 40
    assert counts["critical"] <= 70
    assert counts["recommended"] >= 25
    assert counts["required"] >= 100


def test_critical_nodes_are_critical():
    """Key license-blocking nodes must be critical."""
    g = ObligationGraph()
    must_be_critical = [
        "licensing-spk-permit", "capital-asgari-platform",
        "aml-masak-program", "custody-client-assets",
        "transition-gecis-suresi", "law-6362-art109a-izinsiz-faaliyet",
    ]
    for nid in must_be_critical:
        node = g.get_node(nid)
        assert node is not None, f"{nid} not found"
        assert node["priority"] == "critical", f"{nid} should be critical"


def test_mica_nodes_are_recommended():
    """MiCA reference nodes should be recommended (future-facing)."""
    g = ObligationGraph()
    for n in g.nodes_by_category("mica-reference"):
        assert n["priority"] == "recommended", f"{n['id']} should be recommended"


def test_deadline_type_metadata():
    """Nodes with deadline_type should have valid values."""
    g = ObligationGraph()
    valid_types = {"notification", "reporting", "retention", "transition", "customer_right"}
    dt_count = 0
    for n in g.all_nodes():
        dt = n.get("key_values", {}).get("deadline_type")
        if dt:
            assert dt in valid_types, f"{n['id']} has invalid deadline_type: {dt}"
            dt_count += 1
    assert dt_count >= 30


# -- Penalty Calculator --


def test_penalty_risk_unlicensed():
    """Unlicensed operation should trigger criminal penalties."""
    g = ObligationGraph()
    result = g.calculate_penalty_risk(["unlicensed crypto exchange"])
    assert result["overall_risk_level"] == "CRITICAL"
    assert result["summary"]["criminal_penalties"] > 0
    # Should find art 109/A imprisonment
    all_penalties = result["activity_risk_breakdown"][0]["penalties"]
    penalty_ids = [p["penalty_node_id"] for p in all_penalties]
    assert "law-6362-art109a-izinsiz-faaliyet" in penalty_ids


def test_penalty_risk_aml_violation():
    """AML violations should trigger administrative fines."""
    g = ObligationGraph()
    result = g.calculate_penalty_risk(["AML program eksikligi"])
    assert result["summary"]["total_penalties"] > 0
    all_penalties = result["activity_risk_breakdown"][0]["penalties"]
    assert any(p["fines"] for p in all_penalties)


def test_penalty_risk_custody_misuse():
    """Customer asset misuse should trigger severe criminal penalties."""
    g = ObligationGraph()
    result = g.calculate_penalty_risk(["musteri varligi zimmet"])
    assert result["overall_risk_level"] == "CRITICAL"
    all_penalties = result["activity_risk_breakdown"][0]["penalties"]
    penalty_ids = [p["penalty_node_id"] for p in all_penalties]
    assert "law-6362-art110a-zimmet" in penalty_ids


def test_penalty_risk_market_manipulation():
    """Market manipulation should trigger criminal penalties."""
    g = ObligationGraph()
    result = g.calculate_penalty_risk(["piyasa manipulasyonu"])
    assert result["overall_risk_level"] == "CRITICAL"
    all_penalties = result["activity_risk_breakdown"][0]["penalties"]
    penalty_ids = [p["penalty_node_id"] for p in all_penalties]
    assert "law-6362-art99b-dolandiricilik" in penalty_ids or "penalty-piyasa-dolandiriciligi" in penalty_ids


def test_penalty_risk_multiple_activities():
    """Multiple activities should aggregate penalties without duplicates."""
    g = ObligationGraph()
    result = g.calculate_penalty_risk([
        "lisanssiz faaliyet",
        "musteri varligi zimmet",
        "AML ihlali",
    ])
    assert result["summary"]["total_penalties"] >= 3
    # Each activity should have its own breakdown
    assert len(result["activity_risk_breakdown"]) == 3


def test_penalty_risk_no_match():
    """Activity with no matching obligations should return LOW risk."""
    g = ObligationGraph()
    result = g.calculate_penalty_risk(["yoga studio management"])
    assert result["overall_risk_level"] == "LOW"
    assert result["summary"]["total_penalties"] == 0


def test_penalty_risk_reporting_violation():
    """Reporting violations should trigger administrative fines."""
    g = ObligationGraph()
    result = g.calculate_penalty_risk(["bildirim ihlali"])
    assert result["summary"]["total_penalties"] > 0


def test_penalty_risk_structure():
    """Verify output structure is well-formed."""
    g = ObligationGraph()
    result = g.calculate_penalty_risk(["lisanssiz faaliyet"])
    assert "overall_risk_level" in result
    assert "summary" in result
    assert "activity_risk_breakdown" in result
    entry = result["activity_risk_breakdown"][0]
    assert "activity" in entry
    assert "matched_obligations" in entry
    assert "obligations_with_penalties" in entry
    assert "penalties" in entry
    if entry["penalties"]:
        p = entry["penalties"][0]
        assert "penalty_node_id" in p
        assert "severity" in p
        assert "source_article" in p
        assert p["severity"] in ("criminal", "administrative", "operational")


def test_export_checklist():
    """Verify export_checklist generates a CSV."""
    g = ObligationGraph()
    result = g.export_checklist("platform", "csv")
    
    assert result["success"] is True
    assert result["matched_as"] == "platform"
    assert result["total_exported"] > 20
    assert "file_path" in result
    
    import pathlib
    p = pathlib.Path(result["file_path"])
    assert p.exists()
    assert p.is_file()
    assert p.suffix == ".csv"
    
    # Check contents
    content = p.read_text(encoding="utf-8-sig")
    assert "ID,Kategori,Öncelik,Başlık,Açıklama,Kaynak" in content
    assert "platform" in content.lower()
