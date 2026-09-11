import argparse
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from ats_lead_finder.ats_scraper import ATSScraper
from ats_lead_finder.executive_finder import ExecutiveFinder
from ats_lead_finder.email_verifier import EmailVerifier
from ats_lead_finder.exporter import export_to_csv, export_to_json

console = Console(force_terminal=True)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Free & Automated ATS Lead Finder - Scrape job listings, find decision makers & verify emails."
    )
    parser.add_argument("--role", type=str, required=True, help="Target job role (e.g., 'Software Engineer', 'Data Entry Clerk')")
    parser.add_argument("--location", type=str, default="", help="Target location constraint (e.g., 'Chicago', 'Remote')")
    parser.add_argument("--min-jobs", type=int, default=2, help="Minimum open job listings required per company (default: 2)")
    parser.add_argument("--exec-titles", type=str, nargs="+", default=["CTO", "VP of Engineering", "VP of Technology"], help="Executive target titles")
    parser.add_argument("--output", type=str, default="leads.csv", help="Output file path (CSV format)")
    parser.add_argument("--max-results", type=int, default=50, help="Max search results to query (default: 50)")
    return parser.parse_args()

def main():
    args = parse_args()

    console.print(Panel.fit(
        f"[bold cyan]ATS Lead Finder & Decision Maker Collector[/bold cyan]\n"
        f"[green]Role Target:[/green] {args.role} | [green]Location:[/green] {args.location or 'Global'} | [green]Min Jobs:[/green] >= {args.min_jobs}\n"
        f"[yellow]Executive Titles:[/yellow] {', '.join(args.exec_titles)}\n"
        f"[dim]Zero Paid APIs • 100% Free & Automated[/dim]",
        border_style="cyan"
    ))

    scraper = ATSScraper(max_results=args.max_results)
    exec_finder = ExecutiveFinder()
    verifier = EmailVerifier()

    # Step 1: Scrape ATS Job Listings
    console.print("[cyan]Searching Greenhouse, Lever, Ashby & Workable listings...[/cyan]")
    raw_hits = scraper.search_ats_jobs(role=args.role, location=args.location)
    console.print(f"[bold green]Found {len(raw_hits)} raw ATS job hits.[/bold green]")

    if not raw_hits:
        console.print("[bold red]No job listings found for the query. Try adjusting search parameters.[/bold red]")
        export_to_csv([], args.output)
        export_to_json([], args.output.rsplit(".", 1)[0] + ".json")
        sys.exit(0)

    # Step 2: Aggregate & Filter by min_jobs
    companies = scraper.aggregate_companies(raw_hits, min_jobs=args.min_jobs)
    console.print(f"[bold green][+] Identified {len(companies)} companies hiring >= {args.min_jobs} position(s).[/bold green]")

    if not companies:
        console.print(f"[yellow]No companies met the threshold of hiring >= {args.min_jobs} roles simultaneously.[/yellow]")
        export_to_csv([], args.output)
        export_to_json([], args.output.rsplit(".", 1)[0] + ".json")
        sys.exit(0)

    # Step 3: Find Executives & Verify Emails
    final_leads = []
    console.print(f"[cyan]Processing {len(companies)} decision makers & verifying emails...[/cyan]")

    for idx, comp in enumerate(companies, 1):
        comp_name = comp["company_name"]
        domain = comp["domain"]
        console.print(f"  [{idx}/{len(companies)}] Searching executive for [white]{comp_name}[/white] ({domain})...")

        # Find Executive
        exec_info = exec_finder.find_executive(comp_name, target_titles=args.exec_titles)

        # Verify Email
        email_info = verifier.find_best_email(exec_info["executive_name"], domain)

        lead_record = {
            "company_name": comp_name,
            "company_domain": domain,
            "job_count": comp["job_count"],
            "target_role": args.role,
            "platform": comp["platform"],
            "executive_name": exec_info["executive_name"],
            "executive_title": exec_info["executive_title"],
            "email": email_info["email"],
            "verification_status": email_info["verification_status"],
            "linkedin_url": exec_info["linkedin_url"],
            "job_urls": comp["job_urls"]
        }

        final_leads.append(lead_record)
        time.sleep(0.5)  # Friendly rate limit delay

    # Step 4: Export Leads
    export_to_csv(final_leads, args.output)
    json_output = args.output.rsplit(".", 1)[0] + ".json"
    export_to_json(final_leads, json_output)

    # Step 5: Render Terminal Results Table
    table = Table(title=f"Collected Leads ({len(final_leads)})", show_header=True, header_style="bold magenta")
    table.add_column("Company", style="cyan")
    table.add_column("Open Jobs", justify="center", style="yellow")
    table.add_column("Executive Name", style="white")
    table.add_column("Executive Title", style="dim")
    table.add_column("Verified Email", style="green")
    table.add_column("Status", style="blue")

    for lead in final_leads:
        table.add_row(
            lead["company_name"],
            str(lead["job_count"]),
            lead["executive_name"],
            lead["executive_title"],
            lead["email"],
            lead["verification_status"]
        )

    console.print(table)
    console.print(f"\n[bold green][+] Success! Saved {len(final_leads)} leads to [bold white]{args.output}[/bold white] and [bold white]{json_output}[/bold white][/bold green]\n")

if __name__ == "__main__":
    main()
