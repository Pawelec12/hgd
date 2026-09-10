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

def export_clean_emails_txt(leads: List[Dict[str, Any]], filepath: str) -> bool:
    """Exports a clean list of verified email addresses (one per line) ready for cold emailing."""
    try:
        dirname = os.path.dirname(filepath)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        valid_emails = [lead["email"] for lead in leads if lead.get("email") and not lead["email"].startswith("unknown@")]
        valid_emails = list(dict.fromkeys(valid_emails))  # Unique list

        with open(filepath, mode="w", encoding="utf-8") as f:
            for email in valid_emails:
                f.write(f"{email}\n")
        return True
    except Exception as e:
        print(f"[Error] Text email export failed: {e}")
        return False

def export_to_csv(leads: List[Dict[str, Any]], filepath: str) -> bool:
    """Exports list of lead dicts to CSV file and creates a clean emails.txt file."""
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
                    # Truncate job URLs list to 1 primary link so CSV stays clean and readable
                    row["job_urls"] = row["job_urls"][0] if row["job_urls"] else ""
                writer.writerow(row)

        # Generate clean emails.txt alongside CSV
        txt_path = os.path.join(dirname, "emails.txt") if dirname else "emails.txt"
        export_clean_emails_txt(leads, txt_path)

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
