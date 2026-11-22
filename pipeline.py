"""Read binary-outcome A/B cohorts with uncertainty and sample validity checks."""

import math

TITLE = "Experiment Readout Studio"
DESCRIPTION = "Estimate binary outcome lift by cohort with score intervals, allocation checks and reviewed Markdown readouts."
PROMPT = "Cite cohort counts, denominators and uncertainty. Surface validity flags before interpreting changes. Never equate observational lift with causation."


def wilson(x, n):
    z = 1.959963984540054
    p = x / n
    den = 1 + z * z / n
    middle = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0, middle - half), min(1, middle + half)


def items(data, key, maximum=500):
    if (
        not isinstance(data, dict)
        or not isinstance(data.get(key), list)
        or len(data[key]) > maximum
    ):
        raise ValueError(f"{key} must be an array with up to {maximum} entries.")
    result = {}
    for obj in data[key]:
        if (
            not isinstance(obj, dict)
            or not isinstance(obj.get("id"), str)
            or not obj["id"].strip()
        ):
            raise ValueError(f"Each {key} entry needs a nonempty string ID.")
        if obj["id"] in result:
            raise ValueError(f"Duplicate {key} ID: {obj['id']}.")
        result[obj["id"]] = obj
    return result


def whole(value, name, low=0, high=1_000_000):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be a whole number between {low} and {high}.")
    return value


def label(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} needs nonempty text.")
    return value.strip()


def selected(evidence, approved):
    known = {c["id"]: c for c in evidence["candidates"]}
    accepted = {}
    for choice in approved:
        cid = choice.get("id") if isinstance(choice, dict) else None
        if not isinstance(cid, str) or cid not in known or cid in accepted:
            raise ValueError("Approval contains an unknown or duplicate candidate.")
        note = choice.get("review_note", "")
        if not isinstance(note, str):
            raise ValueError("Review notes must be text.")
        accepted[cid] = note
    return [
        (c, accepted[c["id"]]) for c in evidence["candidates"] if c["id"] in accepted
    ]


def prepare(data: dict) -> dict:
    cohorts = items(data, "cohorts", 250)
    title = label(data.get("experiment"), "experiment")
    minimum = whole(data.get("min_arm_size", 40), "min_arm_size", 1)
    allocation = data.get("expected_treatment_share", 0.5)
    if type(allocation) not in (int, float) or not 0 < allocation < 1:
        raise ValueError("expected_treatment_share must be between zero and one.")
    randomized = data.get("randomized")
    if type(randomized) is not bool:
        raise ValueError("Specify whether assignment was randomized.")
    records = []
    candidates = []
    total = 0
    flagged = 0
    for cid, cohort in sorted(cohorts.items()):
        if type(cohort.get("window_complete")) is not bool:
            raise ValueError(f"{cid}: declare window_complete.")
        counts = {}
        for arm in ("control", "treatment"):
            obs = cohort.get(arm)
            if not isinstance(obs, dict):
                raise ValueError(f"Missing {arm} in {cid}.")
            n = whole(obs.get("exposed"), "exposed", 0, 1_000_000_000)
            x = whole(obs.get("converted"), "converted", 0, n)
            counts[arm] = (x, n)
            records.append(
                {
                    "id": arm + ":" + cid,
                    "Cohort": cid,
                    "Arm": arm,
                    "Exposed": n,
                    "Converted": x,
                    "Window complete": cohort["window_complete"],
                    "Randomized": randomized,
                }
            )
        x0, n0 = counts["control"]
        x1, n1 = counts["treatment"]
        total += n0 + n1
        issues = []
        if not randomized:
            issues.append("Allocation was not randomized")
        if not cohort["window_complete"]:
            issues.append("Observation window incomplete")
        if min(n0, n1) < minimum:
            issues.append(f"Arm below {minimum} observations")
        expected = (n0 + n1) * allocation
        var = expected * (1 - allocation)
        if min(expected, (n0 + n1) * (1 - allocation)) >= 5 and abs(
            n1 - expected
        ) > 3 * math.sqrt(var):
            issues.append(
                "Allocation differs by more than three expected standard deviations"
            )
        estimate = relative = lo = hi = None
        if n0 and n1:
            p0, p1 = x0 / n0, x1 / n1
            diff = p1 - p0
            l0, u0 = wilson(x0, n0)
            l1, u1 = wilson(x1, n1)
            lower = diff - math.hypot(p1 - l1, u0 - p0)
            upper = diff + math.hypot(u1 - p1, p0 - l0)
            estimate, lo, hi = (
                round(100 * v, 3) for v in (diff, max(-1, lower), min(1, upper))
            )
            relative = round(100 * diff / p0, 2) if p0 else None
        else:
            issues.append("Missing arm denominator")
        flagged += int(bool(issues))
        status = "Validity review required" if issues else "Ready for interpretation"
        candidates.append(
            {
                "id": "readout:" + cid,
                "action": f"Include {cid}: {status.lower()}",
                "evidence_ids": ["control:" + cid, "treatment:" + cid],
                "cohort": cid,
                "status": status,
                "control": f"{x0}/{n0}",
                "treatment": f"{x1}/{n1}",
                "difference_pp": estimate,
                "relative_lift_pct": relative,
                "interval_low_pp": lo,
                "interval_high_pp": hi,
                "checks": issues,
            }
        )
    return {
        "summary": f"{title}: {len(cohorts)} cohort comparisons; {flagged} require validity review.",
        "metrics": {
            "Cohorts": len(cohorts),
            "Exposures": total,
            "Flagged cohorts": flagged,
            "Comparisons with both arms": sum(
                c["difference_pp"] is not None for c in candidates
            ),
        },
        "records": records,
        "candidates": candidates,
    }


def export(data, evidence, approved):
    sections = [
        "# Experiment readout",
        "",
        data["experiment"],
        "",
        "Intervals are nominal 95% Newcombe score intervals for an absolute difference in independent proportions.",
    ]
    for c, note in selected(evidence, approved):
        sections += [
            "",
            f"## {c['cohort']}",
            "",
            f"{c['status']}. Control {c['control']}; treatment {c['treatment']}.",
        ]
        if c["difference_pp"] is not None:
            sections.append(
                f"Absolute change: {c['difference_pp']} points (95% interval {c['interval_low_pp']} to {c['interval_high_pp']})."
            )
            sections.append(
                "Relative lift undefined at zero baseline."
                if c["relative_lift_pct"] is None
                else f"Relative lift: {c['relative_lift_pct']}%."
            )
        else:
            sections.append("No numeric estimate: an arm has no exposures.")
        sections.extend("- " + issue for issue in c["checks"])
        if note:
            sections += ["", "Reviewer: " + note]
    return {"experiment-readout.md": "\n".join(sections) + "\n"}
