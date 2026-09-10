import re
import warnings
from typing import Dict, Optional, List

warnings.filterwarnings("ignore")
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

DEFAULT_TITLES = ["CTO", "Chief Technology Officer", "VP of Engineering", "VP of Technology", "Head of Engineering", "Founder", "CEO"]

EXEC_KEYWORDS = [
    "cto", "chief technology officer", "vp of engineering", "vp of technology",
    "vice president of engineering", "head of engineering", "head of technology",
    "founder", "co-founder", "ceo", "chief executive officer", "director of engineering"
]

class ExecutiveFinder:
    def __init__(self):
        pass

    def is_valid_executive_title(self, title_text: str, snippet: str) -> bool:
        """Verifies if title or snippet matches an executive / decision-maker role."""
        combined = f"{title_text} {snippet}".lower()
        return any(kw in combined for kw in EXEC_KEYWORDS)

    def find_executive(self, company_name: str, target_titles: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Searches for executive decision maker profile on LinkedIn.
        Performs strict title filtering to ignore lower-level staff / recruiters.
        """
        titles = target_titles or DEFAULT_TITLES
        titles_dork = " OR ".join([f'"{t}"' for t in titles])
        
        # Primary & Secondary queries
        queries = [
            f'site:linkedin.com/in/ "{company_name}" ({titles_dork})',
            f'"{company_name}" ("CTO" OR "VP of Engineering" OR "Founder" OR "CEO") site:linkedin.com/in/'
        ]

        result_info = {
            "executive_name": "Hiring Manager",
            "executive_title": "CTO / Technology Lead",
            "linkedin_url": ""
        }

        for query in queries:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=5))
                    for r in results:
                        href = r.get("href", "")
                        title_text = r.get("title", "")
                        snippet = r.get("body", "")

                        if "linkedin.com/in/" in href and self.is_valid_executive_title(title_text, snippet):
                            result_info["linkedin_url"] = href
                            parsed_name, parsed_title = self.parse_linkedin_title(title_text, snippet, company_name)
                            if parsed_name and parsed_name.lower() != "unknown":
                                result_info["executive_name"] = parsed_name
                            if parsed_title:
                                result_info["executive_title"] = parsed_title
                            return result_info
            except Exception as e:
                print(f"[Warning] Executive search issue for {company_name}: {e}")

        return result_info

    def parse_linkedin_title(self, raw_title: str, snippet: str, company_name: str) -> tuple[str, str]:
        """
        Parses standard LinkedIn SERP title formats:
        Example: "John Doe - Chief Technology Officer - Stripe | LinkedIn"
        """
        clean_title = raw_title.replace(" | LinkedIn", "").replace(" - LinkedIn", "").strip()
        parts = [p.strip() for p in re.split(r'[-–—|]', clean_title) if p.strip()]

        name = "Unknown"
        title = ""

        if parts:
            name = parts[0]
            # Strip trailing certifications or suffixes
            name = re.sub(r',\s*(Ph\.D\.|MBA|MSc|PMP).*$', '', name, flags=re.IGNORECASE)

        # Match executive title from parts
        for part in parts[1:]:
            part_lower = part.lower()
            if any(kw in part_lower for kw in EXEC_KEYWORDS):
                title = part
                break

        # Fallback snippet title match
        if not title:
            for t in DEFAULT_TITLES:
                if t.lower() in snippet.lower():
                    title = t
                    break

        return name, title or "CTO / Technology Lead"
