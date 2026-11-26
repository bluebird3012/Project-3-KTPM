"""Pure evaluation functions; no browser needed for offline tests."""
from collections import Counter

WCAG_TAGS = ("wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa")
SCAN_TAGS = (*WCAG_TAGS, "best-practice")
# Names/labels and contrast have a zero-tolerance threshold regardless of impact.
KEY_RULES = {"label", "label-title-only", "button-name", "link-name", "select-name",
             "aria-input-field-name", "aria-toggle-field-name", "aria-command-name",
             "aria-dialog-name", "input-button-name", "image-alt", "input-image-alt",
             "frame-title", "color-contrast"}
BUCKETS = ("violations", "incomplete", "passes", "inapplicable")


def wcag(rule):
    return bool(set(rule.get("tags", [])) & set(WCAG_TAGS))


def blocks(rule, node):
    return wcag(rule) and (rule["id"] in KEY_RULES or
                          (node.get("impact") or rule.get("impact")) in {"critical", "serious"})


def evaluate_scan(result, frame_warnings=()):
    if not isinstance(result, dict) or any(not isinstance(result.get(k), list) for k in BUCKETS):
        raise ValueError("Invalid or incomplete axe result")
    if not any(result[k] for k in ("violations", "incomplete", "passes")):
        raise ValueError("No applicable axe rules evaluated")
    counts = Counter()
    findings = []
    for bucket in ("violations", "incomplete"):
        for rule in result[bucket]:
            nodes = rule.get("nodes")
            if not isinstance(nodes, list) or not nodes:
                raise ValueError(f"Missing node evidence for {rule.get('id')}")
            for node in nodes:
                is_wcag = wcag(rule)
                impact = node.get("impact") or rule.get("impact") or "unknown"
                blocking = blocks(rule, node)
                counts[f"{bucket}_nodes"] += 1
                counts[f"{bucket}_{'wcag' if is_wcag else 'best_practice'}"] += 1
                if bucket == "violations":
                    counts[f"violations_{impact}"] += 1
                    if is_wcag:
                        counts[f"wcag_{impact}"] += 1
                if blocking:
                    counts[f"blocking_{bucket}"] += 1
                findings.append({"bucket": bucket, "rule_id": rule["id"], "impact": impact,
                                 "wcag": is_wcag, "blocking": blocking, "tags": rule.get("tags", []),
                                 "target": node.get("target", []), "help": rule.get("help", ""),
                                 "help_url": rule.get("helpUrl", ""),
                                 "failure_summary": node.get("failureSummary", "")})
    if counts["blocking_violations"]:
        status = "FAIL"
    elif counts["blocking_incomplete"] or frame_warnings:
        status = "INCONCLUSIVE"
    else:
        status = "PASS"
    return {"status": status, "rule_counts": {k: len(result[k]) for k in BUCKETS},
            "node_counts": dict(counts), "findings": findings, "frame_warnings": list(frame_warnings)}


def evaluate_keyboard(required, reached, steps, limit, focus_cycle=False):
    if not required or limit < 1 or not set(reached) <= set(required):
        raise ValueError("Invalid keyboard evidence")
    missing = sorted(set(required) - set(reached))
    return {"status": "PASS" if not missing else "FAIL" if steps >= limit or focus_cycle else "INCONCLUSIVE",
            "required": list(required), "reached": list(reached), "missing": missing,
            "steps": steps, "limit": limit, "focus_cycle": focus_cycle}


def evaluate_validation(items):
    # Native validity is evidence of a native validation message, not a proof
    # of screen-reader announcement. DOM errors require a real visible message
    # and a programmatic association with the input.
    observed = [i for i in items if i["message"]]
    if not observed:
        return {"status": "INCONCLUSIVE", "observed_count": 0,
                "unassociated": [], "items": items}
    unassociated = [i["field"] for i in observed if not (i["native"] or i["associated"])]
    return {"status": "FAIL" if unassociated else "PASS", "observed_count": len(observed),
            "unassociated": unassociated, "items": items}


def overall(statuses, expected_count):
    if "FAIL" in statuses:
        return "FAIL"
    if len(statuses) != expected_count or any(s != "PASS" for s in statuses):
        return "INCONCLUSIVE"
    return "PASS"
