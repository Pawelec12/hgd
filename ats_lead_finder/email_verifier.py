import socket
import smtplib
import re
import warnings
from typing import List, Dict, Optional, Tuple
import dns.resolver

warnings.filterwarnings("ignore")
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

class EmailVerifier:
    def __init__(self, sender_email: str = "verify@checkmail.org", timeout: int = 4):
        self.sender_email = sender_email
        self.timeout = timeout

    def split_name(self, full_name: str) -> Tuple[str, str]:
        """Splits full name into clean first and last name."""
        clean = re.sub(r'[^a-zA-Z\s]', '', full_name).strip().lower()
        parts = clean.split()
        if not parts or clean in ["unknown", "hiring manager", "decision maker", "contact"]:
            return ("contact", "")
        if len(parts) == 1:
            return (parts[0], "")
        return (parts[0], parts[-1])

    def detect_domain_pattern(self, domain: str) -> Optional[str]:
        """
        Mines public SERPs to discover actual email patterns used by domain.
        Example: If 'ashrivastava@ocrolus.com' or 'vsmith@ocrolus.com' is found in snippets,
        pattern is 'flast'.
        """
        query = f'"@{domain}"'
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                pattern_regex = re.compile(r'([a-zA-Z0-9._%+-]+)@' + re.escape(domain), re.IGNORECASE)
                
                for r in results:
                    text = f"{r.get('title', '')} {r.get('body', '')}"
                    matches = pattern_regex.findall(text)
                    for m in matches:
                        user_part = m.lower()
                        if user_part not in ["info", "contact", "sales", "support", "jobs", "careers", "help", "admin"]:
                            if "." in user_part:
                                return "first.last"
                            elif len(user_part) >= 4:
                                return "flast"
        except Exception:
            pass
        return None

    def generate_permutations(self, first_name: str, last_name: str, domain: str, detected_pattern: Optional[str] = None) -> List[str]:
        """Generates corporate email pattern permutations ordered by detected domain pattern."""
        f = first_name.lower().strip()
        l = last_name.lower().strip()
        d = domain.lower().strip()

        # If name is unknown / role-based, return clean corporate role emails
        if not f or f in ["unknown", "contact"]:
            return [f"cto@{d}", f"contact@{d}", f"jobs@{d}", f"info@{d}", f"hello@{d}"]

        pattern_map = {
            "first.last": f"{f}.{l}@{d}",
            "flast": f"{f[0]}{l}@{d}",
            "first": f"{f}@{d}",
            "first.l": f"{f}.{l[0]}@{d}",
            "firstl": f"{f}{l[0]}@{d}",
            "firstlast": f"{f}{l}@{d}"
        }

        permutations = []

        # If domain pattern was mined, prioritize it as Candidate #1!
        if detected_pattern and detected_pattern in pattern_map:
            permutations.append(pattern_map[detected_pattern])

        if f and l:
            permutations.extend([
                f"{f[0]}{l}@{d}",      # flast (e.g. ashrivastava@ocrolus.com)
                f"{f}.{l}@{d}",      # first.last (e.g. ajay.shrivastava@ocrolus.com)
                f"{f}@{d}",         # first
                f"{f}.{l[0]}@{d}",    # first.l
                f"{f}{l}@{d}",       # firstlast
                f"{f}{l[0]}@{d}"     # firstl
            ])
        elif f:
            permutations.append(f"{f}@{d}")

        return list(dict.fromkeys(permutations))  # Unique list preserving order

    def get_mx_record(self, domain: str) -> Optional[str]:
        """Queries DNS MX records for domain."""
        try:
            answers = dns.resolver.resolve(domain, 'MX')
            mx_hosts = sorted(answers, key=lambda r: r.preference)
            return str(mx_hosts[0].exchange).rstrip('.')
        except Exception:
            return None

    def verify_smtp(self, domain: str, candidate_emails: List[str]) -> Tuple[str, str]:
        """
        Performs non-intrusive SMTP RCPT TO handshake to test candidate emails.
        Returns (best_email, verification_status).
        """
        mx_host = self.get_mx_record(domain)
        if not mx_host:
            return (candidate_emails[0], "UNVERIFIED_NO_MX")

        try:
            server = smtplib.SMTP(timeout=self.timeout)
            server.connect(mx_host, 25)
            server.helo(socket.gethostname())
            server.mail(self.sender_email)

            # Test catch-all status first using a randomized dummy email
            dummy_email = f"catchall_test_xyz999@{domain}"
            catchall_code, _ = server.rcpt(dummy_email)
            is_catchall = (catchall_code == 250)

            if is_catchall:
                server.quit()
                return (candidate_emails[0], "CATCH_ALL_DOMAIN")

            # Test candidate emails
            for email in candidate_emails:
                code, _ = server.rcpt(email)
                if code == 250:
                    server.quit()
                    return (email, "VERIFIED_SMTP_250")

            server.quit()
            return (candidate_emails[0], "PATTERN_PREDICTED")

        except (socket.timeout, socket.error, smtplib.SMTPException):
            return (candidate_emails[0], "PATTERN_PREDICTED")

    def find_best_email(self, full_name: str, domain: str) -> Dict[str, str]:
        """Complete workflow: Name + Domain -> Pattern Mining -> Verified Email & Status."""
        first, last = self.split_name(full_name)
        pattern = self.detect_domain_pattern(domain)
        candidates = self.generate_permutations(first, last, domain, detected_pattern=pattern)
        best_email, status = self.verify_smtp(domain, candidates)

        return {
            "email": best_email,
            "verification_status": status,
            "all_candidates": ", ".join(candidates[:3])
        }
