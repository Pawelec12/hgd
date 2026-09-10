import re
import urllib.parse
import warnings
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
        Executes Google/DuckDuckGo dorks for major ATS platforms targeting specific role and location.
        Returns a list of raw job search hit dicts.
        """
        query_parts = []
        site_dorks = " OR ".join([f"site:{domain}" for domain in ATS_DOMAINS.values()])
        query = f'({site_dorks}) "{role}"'
        if location:
            query += f' "{location}"'

        results = []
        try:
            with DDGS() as ddgs:
                ddg_results = ddgs.text(query, max_results=self.max_results)
                for r in ddg_results:
                    results.append({
                        "title": r.get("title", ""),
                        "href": r.get("href", ""),
                        "body": r.get("body", "")
                    })
        except Exception as e:
            print(f"[Warning] Search query issue: {e}")

        return results

    def extract_company_slug(self, url: str) -> Dict[str, str]:
        """
        Extracts ATS platform and company slug from ATS job URL.
        Example: https://boards.greenhouse.io/stripe/jobs/123 -> ('greenhouse', 'stripe')
        """
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        path_parts = [p for p in parsed.path.split('/') if p]

        platform = "unknown"
        company_slug = ""

        if "greenhouse.io" in netloc and path_parts:
            platform = "greenhouse"
            company_slug = path_parts[0]
        elif "lever.co" in netloc and path_parts:
            platform = "lever"
            company_slug = path_parts[0]
        elif "ashbyhq.com" in netloc and path_parts:
            platform = "ashby"
            company_slug = path_parts[0]
        elif "workable.com" in netloc and path_parts:
            platform = "workable"
            company_slug = path_parts[0]

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
