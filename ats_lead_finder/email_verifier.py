import socket
import smtplib
import re
from typing import List, Dict, Optional, Tuple
import dns.resolver

class EmailVerifier:
    def __init__(self, sender_email: str = "verify@checkmail.org", timeout: int = 4):
        self.sender_email = sender_email
        self.timeout = timeout

    def split_name(self, full_name: str) -> Tuple[str, str]:
        """Splits full name into clean first and last name."""
        clean = re.sub(r'[^a-zA-Z\s]', '', full_name).strip().lower()
        parts = clean.split()
        if not parts:
            return ("contact", "info")
        if len(parts) == 1:
            return (parts[0], "")
        return (parts[0], parts[-1])

    def generate_permutations(self, first_name: str, last_name: str, domain: str) -> List[str]:
        """Generates standard corporate email pattern permutations."""
        f = first_name.lower().strip()
        l = last_name.lower().strip()
        d = domain.lower().strip()

        if not f and not l:
            return [f"contact@{d}", f"info@{d}"]

        permutations = []
        if f and l:
            permutations.append(f"{f}.{l}@{d}")
            permutations.append(f"{f}@{d}")
            permutations.append(f"{f[0]}{l}@{d}")
            permutations.append(f"{f}.{l[0]}@{d}")
            permutations.append(f"{f}{l}@{d}")
            permutations.append(f"{l}.{f}@{d}")
            permutations.append(f"{f}_{l}@{d}")
            permutations.append(f"{f}{l[0]}@{d}")
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
            # Fallback to top standard pattern if DNS MX fails
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
            return (candidate_emails[0], "PATTERN_GUESS_NO_MATCH")

        except (socket.timeout, socket.error, smtplib.SMTPException):
            # Port 25 blocked or timeout (common on local consumer ISPs)
            # Default to #1 corporate pattern (first.last@domain.com)
            return (candidate_emails[0], "PATTERN_PREDICTED")

    def find_best_email(self, full_name: str, domain: str) -> Dict[str, str]:
        """Complete workflow: Name + Domain -> Verified Email & Status."""
        first, last = self.split_name(full_name)
        candidates = self.generate_permutations(first, last, domain)
        best_email, status = self.verify_smtp(domain, candidates)

        return {
            "email": best_email,
            "verification_status": status,
            "all_candidates": ", ".join(candidates[:3])
        }
