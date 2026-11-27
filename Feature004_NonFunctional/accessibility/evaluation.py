"""Acceptance Criteria evaluation logic for NFR-08 Accessibility Testing."""
from __future__ import annotations

KEY_LABEL_RULES = frozenset({"label", "button-name", "aria-input-field-name", "select-name", "input-button-name"})

PROPOSED_CRITERIA = {
    "critical_violations_max": 0,
    "serious_violations_max": 0,
    "key_label_name_violations_max": 0,
    "color_contrast_violations_max": 0,
    "keyboard_targets_reachable_pct_min": 100.0,
    "keyboard_traps_max": 0,
    "error_association_pct_min": 100.0,
}


def evaluate_axe_result(scenario_id: str, scenario_name: str, axe_raw: dict) -> tuple[dict, list[dict]]:
    violations = axe_raw.get("violations", [])
    passes = axe_raw.get("passes", [])
    incomplete = axe_raw.get("incomplete", [])

    impact_counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    key_label_count = 0
    contrast_count = 0
    flat_rows: list[dict] = []

    for v in violations:
        vid = v.get("id", "")
        impact = (v.get("impact") or "minor").lower()
        nodes = v.get("nodes", [])
        node_count = len(nodes)
        if impact in impact_counts:
            impact_counts[impact] += node_count
        if vid in KEY_LABEL_RULES:
            key_label_count += node_count
        if vid == "color-contrast":
            contrast_count += node_count
        sample_target = ""
        if nodes and nodes[0].get("target"):
            sample_target = " > ".join(str(t) for t in nodes[0]["target"])
        flat_rows.append(
            {
                "scenario_id": scenario_id,
                "rule_id": vid,
                "impact": impact,
                "node_count": node_count,
                "help": v.get("help", ""),
                "help_url": v.get("helpUrl", ""),
                "sample_target": sample_target[:180],
            }
        )

    reasons = []
    if impact_counts["critical"] > PROPOSED_CRITERIA["critical_violations_max"]:
        reasons.append(f"critical={impact_counts['critical']}")
    if impact_counts["serious"] > PROPOSED_CRITERIA["serious_violations_max"]:
        reasons.append(f"serious={impact_counts['serious']}")
    if key_label_count > PROPOSED_CRITERIA["key_label_name_violations_max"]:
        reasons.append(f"key_label_rules={key_label_count}")
    if contrast_count > PROPOSED_CRITERIA["color_contrast_violations_max"]:
        reasons.append(f"color_contrast={contrast_count}")

    verdict = "FAIL" if reasons else "PASS"
    summary_row = {
        "scenario_id": scenario_id,
        "name": scenario_name,
        "kind": "axe",
        "verdict": verdict,
        "violation_rules": len(violations),
        "violation_nodes": sum(len(v.get("nodes", [])) for v in violations),
        "critical_nodes": impact_counts["critical"],
        "serious_nodes": impact_counts["serious"],
        "moderate_nodes": impact_counts["moderate"],
        "minor_nodes": impact_counts["minor"],
        "key_label_nodes": key_label_count,
        "color_contrast_nodes": contrast_count,
        "passes_rules": len(passes),
        "incomplete_rules": len(incomplete),
        "detail": "; ".join(reasons) if reasons else "0 critical/serious/label/contrast violations",
    }
    return summary_row, flat_rows


def evaluate_keyboard_result(
    scenario_id: str,
    scenario_name: str,
    target_ids: list[str],
    reached_ids: set[str],
    trap_detected: bool,
    steps_taken: int,
) -> dict:
    missing = [tid for tid in target_ids if tid not in reached_ids]
    pct = round((len(target_ids) - len(missing)) / len(target_ids) * 100.0, 2) if target_ids else 0.0
    reasons = []
    if missing:
        reasons.append(f"unreachable={missing}")
    if trap_detected:
        reasons.append("keyboard_trap_detected")
    verdict = "FAIL" if reasons else "PASS"
    return {
        "scenario_id": scenario_id,
        "name": scenario_name,
        "kind": "keyboard",
        "verdict": verdict,
        "violation_rules": len(missing) + (1 if trap_detected else 0),
        "violation_nodes": len(missing),
        "critical_nodes": 1 if trap_detected else 0,
        "serious_nodes": len(missing),
        "moderate_nodes": 0,
        "minor_nodes": 0,
        "key_label_nodes": 0,
        "color_contrast_nodes": 0,
        "passes_rules": len(target_ids) - len(missing),
        "incomplete_rules": 0,
        "detail": (
            f"Reached {len(target_ids) - len(missing)}/{len(target_ids)} ({pct}%) in {steps_taken} tabs; "
            + ("; ".join(reasons) if reasons else "no keyboard trap")
        ),
    }


def evaluate_aria_error_result(scenario_id: str, scenario_name: str, checks: list[dict]) -> dict:
    if not checks:
        return {
            "scenario_id": scenario_id,
            "name": scenario_name,
            "kind": "aria_error",
            "verdict": "INCONCLUSIVE",
            "violation_rules": 0,
            "violation_nodes": 0,
            "critical_nodes": 0,
            "serious_nodes": 0,
            "moderate_nodes": 0,
            "minor_nodes": 0,
            "key_label_nodes": 0,
            "color_contrast_nodes": 0,
            "passes_rules": 0,
            "incomplete_rules": 0,
            "detail": "No validation errors observed to evaluate",
        }
    failed = [c for c in checks if not c.get("associated")]
    passed = len(checks) - len(failed)
    pct = round(passed / len(checks) * 100.0, 2)
    verdict = "PASS" if not failed else "FAIL"
    return {
        "scenario_id": scenario_id,
        "name": scenario_name,
        "kind": "aria_error",
        "verdict": verdict,
        "violation_rules": len(failed),
        "violation_nodes": len(failed),
        "critical_nodes": 0,
        "serious_nodes": len(failed),
        "moderate_nodes": 0,
        "minor_nodes": 0,
        "key_label_nodes": 0,
        "color_contrast_nodes": 0,
        "passes_rules": passed,
        "incomplete_rules": 0,
        "detail": f"Associated {passed}/{len(checks)} ({pct}%)" + (
            f"; missing={[c['field'] for c in failed]}" if failed else ""
        ),
    }


def overall_verdict(summary_rows: list[dict]) -> str:
    if any(r["verdict"] == "INCONCLUSIVE" for r in summary_rows):
        return "INCONCLUSIVE"
    if any(r["verdict"] == "FAIL" for r in summary_rows):
        return "FAIL"
    return "PASS"
