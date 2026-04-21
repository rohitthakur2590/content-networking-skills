---
name: network-triage-workflow
description: >
  Triage bug reports, CI failures, and GitHub issues for Ansible network
  collections (cisco.ios, cisco.iosxr, arista.eos, ansible.netcommon, etc.).
  Two modes: (1) Scan mode — run ansible-network-triager to surface all
  unassigned issues and failing CI across repos, then generate a triage
  report. (2) Direct triage — take a single issue/failure, check known
  CI patterns, assess severity, and recommend resolution.
version: "1.0"
type: workflow
requires:
  - triage-workflow
  - jira-integration
  - session-recorder
triggers:
  - "triage network"
  - "triage collection issue"
  - "triage ci failure"
  - "network bug triage"
  - "run triager"
  - "scan network issues"
  - "weekly triage"
---

# Network Collection Triage Workflow

This skill **extends `triage-workflow`** (from harness) with knowledge specific
to Ansible network collections. It does NOT replace the base triage steps — it
adds networking context on top of them.

---

## What This Skill Adds Over Base Triage

The base `triage-workflow` from harness knows how to:
- Gather context from a bug report or CI failure
- Search Jira for duplicates
- Assess severity using a general matrix
- Create/update Jira issues

This networking extension adds:
- **Network severity escalators** that override the base severity assessment
- **Cross-collection dependency chain awareness** (netcommon cascades)
- **Scan mode** using `ansible-network-triager` tool for weekly bulk triage
- **Network collections in scope** (which repos, modules, connection types)

---

## Network Collections in Scope

| Collection | Platform | Primary Connection |
|---|---|---|
| `ansible.netcommon` | Shared (connection plugins, base classes) | N/A |
| `ansible.utils` | Shared (utility filters, cli_parse) | N/A |
| `cisco.ios` | Cisco IOS / IOS-XE | network_cli |
| `cisco.iosxr` | Cisco IOS-XR | network_cli, netconf |
| `cisco.nxos` | Cisco NX-OS | network_cli, httpapi |
| `arista.eos` | Arista EOS | network_cli, httpapi |
| `junipernetworks.junos` | Juniper JunOS | network_cli, netconf |
| `cisco.asa` | Cisco ASA | network_cli |
| `vyos.vyos` | VyOS | network_cli |

---

## Mode 1: Scan Mode (Weekly Triage)

Use this when you want to surface ALL unassigned issues and failing CI
across network collection repos. Typically run weekly when the triager
email arrives or during scheduled triage meetings.

### How It Works

The `ansible-network-triager` tool queries the GitHub API for:
- **Bug mode** (`--bugs`): All issues and PRs with `assignee=none` created
  in the last N days across all configured repos
- **CI mode** (`--ci`): Latest scheduled workflow run status for each repo

### Step-by-Step

#### 1. Run the triager tool

```bash
# Bug scrub — find unassigned issues/PRs from last 14 days
cd /path/to/ansible-network-triager
python -m triager --bugs -c config.yaml

# CI report — check latest workflow status per repo
python -m triager --ci -c config.yaml
```

The tool outputs a prettytable with columns: Repo | Title | URL | Type (for bugs)
or Repo | Status | URL (for CI).

#### 2. For structured output, use the JSON wrapper

The triager's native output is a prettytable (text). For structured processing,
use the `triager-json.py` wrapper included with this skill:

```bash
# From the content-networking-skills repo
python skills/network-triage-workflow/triager-json.py \
  --bugs \
  --triager-path /path/to/ansible-network-triager \
  --config /path/to/ansible-network-triager/config.yaml
```

This outputs structured JSON:
```json
{
  "mode": "bugs",
  "timestamp": "2026-04-21T10:30:00",
  "since_days": 14,
  "repos": {
    "cisco.ios": [
      {
        "title": "Multi-range interface commands for ios_config",
        "url": "https://github.com/ansible-collections/cisco.ios/pull/1324",
        "type": "Pull Request"
      }
    ],
    "cisco.iosxr": [...],
    "arista.eos": [...]
  },
  "summary": {
    "total_items": 11,
    "by_repo": {"cisco.ios": 6, "cisco.iosxr": 2, "arista.eos": 3},
    "by_type": {"Pull Request": 9, "Issue": 2}
  }
}
```

#### 3. Categorize each item

For each item from the triager output:

1. **Classify the type**: Downstream fix, New feature PR, Bug report, Chore/CI, Molecule/test improvement
2. **Check for cross-collection signals**: Multiple repos showing similar failures = likely cascade
3. **Assign priority**: Use the severity matrix + network escalators (see below)

#### 4. Generate a triage summary

After processing all items, produce a summary:
- Total items by repo and type
- Items matching known CI patterns (quick resolution)
- Items needing deep triage (new/unknown issues)
- Cross-collection signals detected
- Recommended action order (highest priority first)

---

## Mode 2: Direct Triage (Single Issue)

Use this when someone reports a specific bug, CI failure, or GitHub issue
and you need to triage it deeply.

### Step 1 — Run Base Triage Workflow

Run the base `triage-workflow` steps (loaded via `requires`). The base handles:
context gathering, duplicate search, severity assessment, and Jira creation.

Then apply these **networking-specific additions**:

### Network Severity Escalators

Apply AFTER the base severity assessment. These can only RAISE severity, never lower it.

| Condition | Action |
|---|---|
| Bug is in `ansible.netcommon` or `ansible.utils` | **Always Critical** — cascade risk to all downstream collections |
| Affected collection is a certified/validated version | Bump severity **+1 level** (Minor→Major, Major→Critical) |
| Bug reported by or affecting a strategic customer | **Critical** regardless of base assessment |
| Bug causes data loss or security issue | **Critical** regardless of base assessment |
| Multiple collections failing with same root cause | **Critical** — cascade event in progress |

### Cross-Collection Dependency Check

If the bug is in `ansible.netcommon` or `ansible.utils`:
1. List ALL downstream collections that import the affected code
2. Check if their CI is currently failing (quick GitHub Actions check)
3. If multiple collections are failing → this is a cascade event
4. Create a SINGLE Jira issue covering the cascade, link all affected collections
5. Priority action: fix in netcommon → cut release → re-trigger downstream CI

Dependency chain:
```
ansible.netcommon ──→ cisco.ios
                  ──→ cisco.iosxr
                  ──→ cisco.nxos
                  ──→ arista.eos
                  ──→ junipernetworks.junos
                  ──→ cisco.asa
                  ──→ vyos.vyos

ansible.utils ────→ (same downstream consumers)
```

---

## Triage Output Format

Every triage session should produce a structured report:

```markdown
## Network Collection Triage Report

**Date**: [date]
**Mode**: [Scan / Direct]
**Triaged by**: [name]

### Issue
[GitHub issue URL or CI failure link]

### Collection: [e.g. cisco.ios]
### Component: [module name, plugin, or CI infrastructure]
### Ansible Version: [e.g. stable-2.19 / devel]
### Connection Type: [network_cli / netconf / httpapi]

### Known Pattern Match
[Pattern N: name — OR "No known pattern, new issue"]

### Severity: [Critical / Major / Minor / Trivial]
[Justification, including any escalators applied]

### Cross-Collection Impact
[None / List of affected collections / Cascade event detected]

### Root Cause
[Technical explanation if identified]

### Recommended Resolution
[Specific action: cut release, fix in PR #N, add meta: reset_connection, etc.]

### Jira
[Created ANSTRAT-XXXX / Updated existing / Duplicate of existing]
```

---

## Dashboard Output (HTML)

After completing triage (scan mode), generate a visual HTML dashboard from
the **empty template** at `templates/triage-dashboard.html`.

The template contains ALL the CSS, layout, and JavaScript — but NO data.
It uses `{{ PLACEHOLDER }}` markers and commented-out HTML blocks that you
duplicate and populate with real triage results.

### What the Dashboard Contains

1. **Header** — date, period, collections scanned, skill version
2. **Pipeline diagram** — (static, already in template, don't change)
3. **Stats bar** — total items, PRs vs Issues, signals detected, items needing deep triage
4. **Repo breakdown** — item count per collection
5. **Cross-collection signals** — highlighted box if downstream fixes or cascade events detected
6. **Categorized items** — grouped by type (test improvements, features, chores, downstream fixes, bugs), each as an expandable card with triage details and recommended action
7. **Priority summary** — ordered action list for the week
8. **Time savings banner** — manual vs agentic triage comparison

### How to Generate

After completing all triage analysis:

1. Read the template file `templates/triage-dashboard.html`
2. Copy the entire file contents as a starting point
3. Replace all `{{ PLACEHOLDER }}` values with real data from this triage session:
   - `{{ DATE }}` → today's date
   - `{{ PERIOD }}` → lookback period (e.g. "Last 14 days")
   - `{{ COLLECTIONS }}` → collections scanned (e.g. "cisco.ios · cisco.iosxr")
   - `{{ TOTAL_ITEMS }}`, `{{ TOTAL_PRS }}`, `{{ TOTAL_ISSUES }}` → actual counts
   - `{{ DEEP_TRIAGE_COUNT }}`, `{{ SIGNAL_COUNT }}`, `{{ SERIES_COUNT }}` → detected counts
4. Uncomment and duplicate the template blocks:
   - **REPO STAT** blocks — one per repo scanned
   - **SIGNAL BOX** blocks — one per cross-collection signal detected (omit section entirely if none)
   - **CATEGORY GROUP** blocks — one per category found (test, feature, chore, downstream, bug)
   - **ISSUE CARD** blocks — one per triaged item, inside its category group
   - **PRIORITY ITEM** blocks — one per priority action, highest priority first
5. For each issue card, set:
   - `{{ GITHUB_URL }}` — the actual GitHub PR/issue URL (makes the tag clickable)
   - `{{ TYPE_CSS }}` — `type-pr` or `type-issue`
   - `{{ SEV_CLASS }}` — `sev-critical`, `sev-major`, `sev-minor`, or `sev-trivial`
   - Triage body sections with real assessment, root cause, recommended action
6. Fill the time savings banner with actual estimates based on item count
7. Save as `triage-report-YYYY-MM-DD.html` in the current working directory
8. Share the file link with the user

### Styling Reference

All CSS is already in the template. Use these classes:

- **Severity badges**: `sev-critical` (red), `sev-major` (orange), `sev-minor` (green), `sev-trivial` (blue)
- **Type tags**: `type-pr` (green), `type-issue` (orange) — these are `<a>` tags linking to GitHub
- **Category labels**: `cat-test` (green), `cat-feature` (blue), `cat-chore` (purple), `cat-downstream` (orange), `cat-bug` (red)
- **Signal tags**: `signal-tag` (red) for cross-collection signals
- **Series tags**: `series-tag` (teal) for related PR series
- **Priority dots**: `dot-red` (urgent), `dot-orange` (high), `dot-yellow` (medium), `dot-green` (low)

### When to Generate

- **Always** generate for scan mode (weekly triage)
- **Skip** for single direct issue triage (unless user requests it)
- **Skip** if user explicitly asks for text-only output

---

## Setup: ansible-network-triager

The triager tool is a separate Python CLI that queries GitHub for issues and CI status.

### One-Time Setup

```bash
# 1. Clone the triager
git clone https://github.com/ansible-network/ansible-network-triager.git
cd ansible-network-triager

# 2. Install
pip install -e .

# 3. Set your GitHub token
export GITHUB_TOKEN="ghp_your_token_here"

# 4. Set repo configuration (which repos to scan)
export REPO_CONFIG='{
  "ansible-collections": {
    "ci_and_bug_repos": [
      "cisco.ios",
      "cisco.iosxr",
      "cisco.nxos",
      "arista.eos",
      "junipernetworks.junos",
      "cisco.asa",
      "ansible.netcommon",
      "ansible.utils"
    ],
    "bug_specific_repos": [
      "community.yang"
    ]
  },
  "redhat-cop": {
    "ci_and_bug_repos": [
      "network.interfaces",
      "network.bgp",
      "network.base"
    ]
  }
}'

# 5. Verify it works
python -m triager --bugs -c config.yaml
```

### config.yaml

The triager needs a `config.yaml` with:
```yaml
organization_name: "Ansible Networking"
workflow_name: "tests.yml"
timedelta: 14    # Look back N days for issues
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | Yes | GitHub personal access token with repo read access |
| `REPO_CONFIG` | Yes | JSON mapping of GitHub orgs → repos to scan (see above) |
| `MAINTAINERS` | No | JSON list of `{"name": "...", "email": "..."}` for email reports |
| `EMAIL_SENDER` | No | Gmail address for sending triage emails |
| `EMAIL_PASSWORD` | No | Gmail app password for sending triage emails |
