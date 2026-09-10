# Automated ATS Lead Finder & Decision Maker Email Collector

A 100% **free** and **automated** CLI tool and GitHub Action workflow that:
1. **Identifies Intent**: Scrapes Applicant Tracking Systems (`Greenhouse`, `Lever`, `Ashby`, `Workable`) for companies hiring 2+ positions in target roles.
2. **Finds Executives**: Uses search engine dorks to locate CTOs, VPs of Technology, and VPs of Engineering on LinkedIn.
3. **Verifies Emails at $0 Cost**: Generates corporate email pattern candidates and performs non-intrusive SMTP DNS MX handshakes to verify mailbox existence without paid APIs.

---

## Features

- 💰 **100% Free**: No paid APIs, Apollo subscriptions, or LinkedIn Sales Navigator required.
- ⚡ **Zero-Install Cloud Automation**: Includes GitHub Actions workflow to run searches in the cloud and download CSV artifacts.
- 🎯 **High Intent Filtering**: Targets companies actively hiring multiple roles simultaneously.
- ✉️ **Built-in SMTP Mailbox Verification**: Validates email pattern existence using raw DNS MX records.

---

## Quickstart (Run Locally)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/YOUR_USERNAME/ats-lead-finder.git
cd ats-lead-finder
pip install -r requirements.txt
```

### 2. Run Lead Finder
Collect decision-maker emails for companies hiring 2+ Data Entry Clerks or Software Engineers:
```bash
python main.py --role "Software Engineer" --location "Chicago" --min-jobs 2 --output leads.csv
```

### Options & Flags
| Argument | Description | Default |
| :--- | :--- | :--- |
| `--role` | Target job title to search (Required) | *None* |
| `--location` | Target location restriction (Optional) | `""` (Global) |
| `--min-jobs` | Minimum open roles required per company | `2` |
| `--exec-titles` | Target executive titles | `CTO` `VP of Engineering` `VP of Technology` |
| `--output` | Output file path | `leads.csv` |

---

## How to Run on GitHub (100% Cloud Automated)

You don't even need to run this on your computer! You can host it on a free GitHub repository:

1. **Push this folder to a new GitHub Repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of ATS Lead Finder"
   git remote add origin https://github.com/YOUR_USERNAME/ats-lead-finder.git
   git push -u origin main
   ```
2. Go to your repository tab on GitHub: **Actions** -> **ATS Lead Finder Automation**.
3. Click **Run workflow**, enter your target `--role` and `--location`, and click **Run**.
4. When complete, download `leads.csv` under the **Artifacts** section of the workflow run!

---

## Generated Lead Output Format (`leads.csv`)

| company_name | job_count | target_role | executive_name | executive_title | email | verification_status | linkedin_url |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Acme Corp | 3 | Software Engineer | John Doe | CTO | `john.doe@acme.com` | `VERIFIED_SMTP_250` | `https://linkedin.com/in/...` |

---

## License
MIT License - Open Source & Free for Commercial/Personal Use.
