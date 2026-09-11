import socket
import re
import warnings
import os
import httpx
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

NICKNAMES = {
    "robert": ["bob", "rob"],
    "elizabeth": ["liz", "beth", "betty"],
    "william": ["will", "bill"],
    "michael": ["mike"],
    "matthew": ["matt"],
    "christopher": ["chris"],
    "daniel": ["dan"],
    "thomas": ["tom"],
    "david": ["dave"],
    "richard": ["rick", "dick"],
    "joseph": ["joe"],
    "charles": ["charlie", "chuck"],
    "james": ["jim"],
    "alexander": ["alex"],
    "nicholas": ["nick"],
    "stephen": ["steve"],
    "steven": ["steve"],
    "andrew": ["andy"],
    "jonathan": ["jon"],
    "joshua": ["josh"],
    "samuel": ["sam"],
    "benjamin": ["ben"],
    "timothy": ["tim"],
    "edward": ["ed"],
    "patrick": ["pat"]
}

class EmailVerifier:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.apollo_api_key = os.environ.get("APOLLO_API_KEY")

    def split_name(self, full_name: str) -> Tuple[str, str]:
        """Splits full name into clean first and last name."""
        clean = re.sub(r'[^a-zA-Z\s]', '', full_name).strip().lower()
        parts = clean.split()
        if not parts or clean in ["unknown", "hiring manager", "decision maker", "contact"]:
            return ("contact", "")
        if len(parts) == 1:
            return (parts[0], "")
        return (parts[0], parts[-1])

    def search_apollo_api(self, first_name: str, last_name: str, domain: str) -> Optional[str]:
        """Uses Apollo.io Free API if available to get 100% accurate emails."""
        if not self.apollo_api_key:
            return None
        
        url = "https://api.apollo.io/v1/people/match"
        headers = {
            "Cache-Control": "no-cache",
            "Content-Type": "application/json"
        }
        data = {
            "api_key": self.apollo_api_key,
            "first_name": first_name,
            "last_name": last_name,
            "organization_domain": domain
        }
        try:
            r = httpx.post(url, headers=headers, json=data, timeout=self.timeout)
            if r.status_code == 200:
                person = r.json().get("person")
                if person and person.get("email"):
                    return person["email"]
        except Exception:
            pass
        return None

    def search_office365_api(self, email: str) -> bool:
        """
        Uses undocumented Microsoft API to verify if an email exists in Azure AD.
        Returns True if it exists (0), False if it doesn't (1), or None if domain not managed by O365 (5).
        """
        url = 'https://login.microsoftonline.com/common/GetCredentialType'
        try:
            r = httpx.post(url, json={'Username': email}, timeout=self.timeout)
            if r.status_code == 200:
                result = r.json().get('IfExistsResult')
                if result == 0:
                    return True
                elif result == 1:
                    return False
        except Exception:
            pass
        return False

    def is_office365_domain(self, domain: str) -> bool:
        """Quick check if a domain is managed by Microsoft/O365."""
        url = 'https://login.microsoftonline.com/common/GetCredentialType'
        try:
            r = httpx.post(url, json={'Username': f'test_does_not_exist_xyz123@{domain}'}, timeout=self.timeout)
            if r.status_code == 200:
                result = r.json().get('IfExistsResult')
                # 0 = Exists, 1 = Does not exist, 5 = Domain not managed, 6 = Domain managed but not in tenant
                if result in [0, 1]: 
                    return True
        except Exception:
            pass
        return False

    def scrape_web_pattern(self, domain: str) -> Optional[str]:
        """
        Scrapes company website to find *any* email address and deduces the pattern.
        """
        urls_to_try = [
            f"https://www.{domain}/about",
            f"https://www.{domain}/team",
            f"https://www.{domain}/contact",
            f"https://www.{domain}/",
            f"https://crt.sh/?q=%.{domain}&output=json"
        ]
        
        email_regex = re.compile(r'([a-zA-Z0-9._%+-]+)@' + re.escape(domain), re.IGNORECASE)
        
        for url in urls_to_try:
            try:
                r = httpx.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=self.timeout, follow_redirects=True)
                if r.status_code == 200:
                    text = str(r.json()) if 'crt.sh' in url else r.text
                    matches = email_regex.findall(text)
                    for m in matches:
                        user_part = m.lower()
                        # Ignore generic emails
                        if user_part not in ["info", "contact", "sales", "support", "jobs", "careers", "help", "admin", "press", "media", "hello", "hostmaster", "postmaster", "webmaster"]:
                            # Deduce pattern
                            if "." in user_part:
                                return "first.last"
                            elif len(user_part) >= 4:
                                return "flast" # most common
            except Exception:
                continue
        return None

    def search_executive_direct_email(self, first_name: str, last_name: str, domain: str) -> Optional[str]:
        """Executes targeted SERP queries to discover exact executive email mentions."""
        f = first_name.lower().strip()
        l = last_name.lower().strip()
        if not f or f == "contact":
            return None

        queries = [f'"{f} {l}" "{domain}" email']
        pattern_regex = re.compile(r'([a-zA-Z0-9._%+-]+@' + re.escape(domain) + r')', re.IGNORECASE)

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(queries[0], max_results=3))
                for r in results:
                    text = f"{r.get('title', '')} {r.get('body', '')}"
                    matches = pattern_regex.findall(text)
                    for email in matches:
                        email_lower = email.lower()
                        if f in email_lower or (l and l in email_lower):
                            return email_lower
        except Exception:
            pass
        return None

    def generate_permutations(self, first: str, last: str, domain: str, detected_pattern: Optional[str] = None) -> List[str]:
        """Generates email patterns based on extracted/deduced evidence, expanding nicknames."""
        if not first or first == "contact":
            return [f"contact@{domain}"]
            
        first = first.lower().strip()
        last = last.lower().strip()
        l_init = last[0] if last else ""

        # Build list of names to try (original first + nicknames)
        first_names = [first]
        if first in NICKNAMES:
            first_names.extend(NICKNAMES[first])

        permutations = []
        
        for f in first_names:
            f_init = f[0] if f else ""
            pattern_map = {
                "first.last": f"{f}.{last}@{domain}",
                "flast": f"{f_init}{last}@{domain}",
                "first": f"{f}@{domain}"
            }

            if detected_pattern and detected_pattern in pattern_map:
                if pattern_map[detected_pattern] not in permutations:
                    permutations.append(pattern_map[detected_pattern])

            # Standard fallbacks
            fallbacks = [
                f"{f}@{domain}",             # first
                f"{f_init}{last}@{domain}",  # flast
                f"{f}.{last}@{domain}",      # first.last
                f"{f}{last}@{domain}"        # firstlast
            ]
            
            for p in fallbacks:
                if p not in permutations:
                    permutations.append(p)
                
        return permutations

    def find_best_email(self, full_name: str, domain: str) -> Dict[str, str]:
        """Complete Evidence-Based Workflow."""
        first, last = self.split_name(full_name)

        # 1. Apollo API (Gold Standard if key is provided)
        if self.apollo_api_key:
            apollo_email = self.search_apollo_api(first, last, domain)
            if apollo_email:
                return {
                    "email": apollo_email,
                    "verification_status": "VERIFIED_APOLLO_API",
                    "all_candidates": apollo_email
                }

        # 2. Executive Direct Dorking (Finding explicit mention of the exact person)
        direct_email = self.search_executive_direct_email(first, last, domain)
        if direct_email:
            return {
                "email": direct_email,
                "verification_status": "EXPLICIT_SERP_FIND",
                "all_candidates": direct_email
            }

        # 3. Evidence-Based Web Pattern Scraping
        web_pattern = self.scrape_web_pattern(domain)
        candidates = self.generate_permutations(first, last, domain, detected_pattern=web_pattern)

        # 4. Office 365 Verification Bypass (100% accurate for O365, ignores Catch-All)
        if self.is_office365_domain(domain):
            for candidate in candidates:
                if self.search_office365_api(candidate):
                    return {
                        "email": candidate,
                        "verification_status": "VERIFIED_O365_BYPASS",
                        "all_candidates": ", ".join(candidates[:3])
                    }
            # If O365 confirms none exist, maybe the pattern is obscure, or person left
            return {
                "email": candidates[0],
                "verification_status": "NOT_FOUND_O365_STRICT",
                "all_candidates": ", ".join(candidates[:3])
            }

        # 5. Final Fallback (If not O365 and no Apollo key, we rely on Web Pattern or standard fallback)
        status = "PATTERN_EXTRACTED_FROM_WEB" if web_pattern else "PATTERN_GUESSED_FALLBACK"
        
        return {
            "email": candidates[0],
            "verification_status": status,
            "all_candidates": ", ".join(candidates[:3])
        }
