import re
import warnings
from typing import Dict, Optional, List

warnings.filterwarnings("ignore")
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

DEFAULT_TITLES = ["CTO", "Chief Technology Officer", "VP of Engineering", "VP of Technology", "Head of Engineering"]

class ExecutiveFinder:
    def __init__(self):
        pass

    def find_executive(self, company_name: str, target_titles: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Searches search engine for executive profile on LinkedIn for target company.
        Extracts Name, Title, and LinkedIn URL.
        """
        titles = target_titles or DEFAULT_TITLES
        titles_dork = " OR ".join([f'"{t}"' for t in titles])
        query = f'site:linkedin.com/in/ "{company_name}" ({titles_dork})'

        result_info = {
            "executive_name": "Unknown",
            "executive_title": titles[0],
            "linkedin_url": ""
        }

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                for r in results:
                    href = r.get("href", "")
                    title_text = r.get("title", "")
                    snippet = r.get("body", "")

                    if "linkedin.com/in/" in href:
                        result_info["linkedin_url"] = href
                        parsed_name, parsed_title = self.parse_linkedin_title(title_text, snippet, company_name)
                        if parsed_name:
                            result_info["executive_name"] = parsed_name
                        if parsed_title:
                            result_info["executive_title"] = parsed_title
                        break
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
            # Strip trailing certifications or suffixes if present
            name = re.sub(r',\s*(Ph\.D\.|MBA|MSc|PMP).*$', '', name, flags=re.IGNORECASE)

        if len(parts) >= 2:
            title = parts[1]

        # Fallback snippet title match if title part missing
        if not title:
            for t in DEFAULT_TITLES:
                if t.lower() in snippet.lower():
                    title = t
                    break

        return name, title or "Executive / Decision Maker"
