"""
Diff helper for the Parking Leads agent.

Compares a baseline snapshot of a parking_protocols_*.json DB against the
current DB, and writes a markdown table of the NEW projects (those whose
{city, address} key did not exist in the baseline).

Usage:
    python parking_leads_diff.py <baseline.json> <current.json> <out_report.md> <city_label> <date>

Prints a JSON summary to stdout: {"new_count": N, "total": M}
"""
import sys, json, os


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def key(rec):
    return (str(rec.get("city", "")).strip(), str(rec.get("address", "")).strip())


def cell(rec, field, limit=160):
    """Sanitize a field value for a markdown table cell."""
    val = rec.get(field)
    if val is None or val == "None":
        return ""
    return str(val).replace("\n", " ").replace("|", "/").strip()[:limit]


def main():
    baseline, current, out_md, label, date = sys.argv[1:6]
    base, cur = load(baseline), load(current)
    base_keys = {key(r) for r in base}
    new = [r for r in cur if key(r) not in base_keys]

    lines = [
        f"# לידים חדשים — מתקני חניה ({label}) — {date}",
        "",
        f"נמצאו **{len(new)}** פרויקטים חדשים (מתוך {len(cur)} ב-DB).",
        "",
    ]
    if new:
        lines += [
            "| כתובת | סוג מתקן | מס׳ חניות | גוש | חלקה | תאריך | תיאור |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in new:
            lines.append(
                "| {} | {} | {} | {} | {} | {} | {} |".format(
                    cell(r, "address"),
                    cell(r, "device_types"),
                    cell(r, "parking_count"),
                    cell(r, "gush"),
                    cell(r, "helka"),
                    cell(r, "dates"),
                    cell(r, "description", 120),
                )
            )
    else:
        lines.append("_אין פרויקטים חדשים השבוע._")

    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps({"new_count": len(new), "total": len(cur)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
