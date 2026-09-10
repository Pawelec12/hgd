import csv
import json
import os
from typing import List, Dict, Any

FIELDNAMES = [
    "company_name",
    "company_domain",
    "job_count",
    "target_role",
    "platform",
    "executive_name",
    "executive_title",
    "email",
    "verification_status",
    "linkedin_url",
    "job_urls"
]

def export_to_csv(leads: List[Dict[str, Any]], filepath: str) -> bool:
    """Exports list of lead dicts to CSV file."""
    try:
        dirname = os.path.dirname(filepath)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            for lead in leads:
                row = lead.copy()
                if isinstance(row.get("job_urls"), list):
                    row["job_urls"] = " | ".join(row["job_urls"])
                writer.writerow(row)
        return True
    except Exception as e:
        print(f"[Error] CSV export failed: {e}")
        return False

def export_to_json(leads: List[Dict[str, Any]], filepath: str) -> bool:
    """Exports list of lead dicts to JSON file."""
    try:
        dirname = os.path.dirname(filepath)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(leads, f, indent=2)
        return True
    except Exception as e:
        print(f"[Error] JSON export failed: {e}")
        return False
