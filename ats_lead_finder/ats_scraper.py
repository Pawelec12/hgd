import re
import urllib.parse
import warnings
import time
from typing import Dict, List, Any
import httpx
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")
from duckduckgo_search import DDGS

ATS_DOMAINS = {
    "greenhouse": "boards.greenhouse.io",
    "lever": "jobs.lever.co",
    "ashby": "jobs.ashbyhq.com",
    "workable": "apply.workable.com"
}

class ATSScraper:
    def __init__(self, max_results: int = 50):
        self.max_results = max_results
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def search_ats_jobs(self, role: str, location: str = "") -> List[Dict[str, str]]:
        """
        Executes search queries per ATS platform targeting specific role and location.
        Falls back to combined query if per-domain searches are rate-limited.
        """
        results = []
        seen_urls = set()
        per_domain_limit = max(15, self.max_results // len(ATS_DOMAINS))

        for platform, domain in ATS_DOMAINS.items():
            query = f'site:{domain} "{role}"'
            if location:
                query += f' "{location}"'

            try:
                with DDGS() as ddgs:
                    ddg_results = list(ddgs.text(query, max_results=per_domain_limit))
                    for r in ddg_results:
                        href = r.get("href", "")
                        if href and href not in seen_urls:
                            seen_urls.add(href)
                            results.append({
                                "title": r.get("title", ""),
                                "href": href,
                                "body": r.get("body", "")
                            })
                time.sleep(0.3)
            except Exception as e:
                print(f"[Warning] Search query issue for {domain}: {e}")

        # Fallback to combined query if empty
        if not results:
            site_dorks = " OR ".join([f"site:{domain}" for domain in ATS_DOMAINS.values()])
            fallback_query = f'{site_dorks} "{role}"'
            if location:
                fallback_query += f' "{location}"'
            try:
                with DDGS() as ddgs:
                    ddg_results = list(ddgs.text(fallback_query, max_results=self.max_results))
                    for r in ddg_results:
                        href = r.get("href", "")
                        if href and href not in seen_urls:
                            seen_urls.add(href)
                            results.append({
                                "title": r.get("title", ""),
                                "href": href,
                                "body": r.get("body", "")
                            })
            except Exception as e:
                print(f"[Warning] Fallback search query issue: {e}")

        return results

    def extract_company_slug(self, url: str) -> Dict[str, str]:
        """
        Extracts ATS platform and company slug from ATS job URL.
        Example: https://boards.greenhouse.io/stripe/jobs/123 -> ('greenhouse', 'stripe')
        Example: https://boards.greenhouse.io/embed/job_board?for=stripe -> ('greenhouse', 'stripe')
        """
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        path_parts = [p for p in parsed.path.split('/') if p]
        query_params = urllib.parse.parse_qs(parsed.query)

        platform = "unknown"
        company_slug = ""

        # Check query parameters (e.g. ?for=stripe or ?token=stripe)
        for param in ["for", "token", "for_company", "c"]:
            if param in query_params and query_params[param]:
                company_slug = query_params[param][0]
                break

        if "greenhouse.io" in netloc:
            platform = "greenhouse"
            if not company_slug and path_parts:
                if path_parts[0] not in ["embed", "jobs", "careers", "api"]:
                    company_slug = path_parts[0]
                elif len(path_parts) > 1 and path_parts[1] not in ["job_board", "jobs"]:
                    company_slug = path_parts[1]
        elif "lever.co" in netloc:
            platform = "lever"
            if not company_slug and path_parts:
                company_slug = path_parts[0]
        elif "ashbyhq.com" in netloc:
            platform = "ashby"
            if not company_slug and path_parts:
                company_slug = path_parts[0]
        elif "workable.com" in netloc:
            platform = "workable"
            if not company_slug and path_parts:
                company_slug = path_parts[0]

        # Clean slug
        company_slug = company_slug.strip().lower()

        return {
            "platform": platform,
            "company_slug": company_slug
        }

    def aggregate_companies(self, raw_results: List[Dict[str, str]], min_jobs: int = 2) -> List[Dict[str, Any]]:
        """
        Groups job hits by company slug, counts job listings, and filters by min_jobs.
        Infers company website domain name from slug.
        """
        companies: Dict[str, Dict[str, Any]] = {}

        for item in raw_results:
            url = item["href"]
            extracted = self.extract_company_slug(url)
            slug = extracted["company_slug"]
            platform = extracted["platform"]

            if not slug or slug.lower() in ["embed", "jobs", "careers", "api"]:
                continue

            if slug not in companies:
                # Clean up slug into display company name
                clean_name = slug.replace("-", " ").replace("_", " ").title()
                companies[slug] = {
                    "company_slug": slug,
                    "company_name": clean_name,
                    "platform": platform,
                    "domain": f"{slug}.com",  # Default guess, resolved in verifier if needed
                    "job_urls": [],
                    "job_count": 0
                }

            if url not in companies[slug]["job_urls"]:
                companies[slug]["job_urls"].append(url)
                companies[slug]["job_count"] += 1

        # Filter by min_jobs threshold
        filtered = [comp for comp in companies.values() if comp["job_count"] >= min_jobs]
        
        # Sort descending by job count
        filtered.sort(key=lambda x: x["job_count"], reverse=True)
        return filtered
