# content-networking-skills

AI skills for Ansible network collection development — CI triage, test execution, and cross-collection tooling. Extends [aap-sdlc-harness](https://gitlab.cee.redhat.com/aap-agentic-tooling/harness) base workflows.

## Quick Start

### Prerequisites

Install the harness base skills first (our skills extend them via `requires`):

```bash
/plugin marketplace add ansible/ai-marketplace-internal
/plugin install aap-sdlc-harness@ai-marketplace-internal
```

### Install networking skills

```bash
/plugin install content-networking@ai-marketplace-internal
```

Or install locally for development:

```bash
# Clone this repo
git clone https://github.com/ansible-network/content-networking-skills.git

# Point Claude Code to it
# Add to .claude/settings.json:
#   "skills": ["./path/to/content-networking-skills/skills/network-triage-workflow"]
```

## Available Skills

| Skill | Extends | Triggers | Description |
|---|---|---|---|
| `network-triage-workflow` | `triage-workflow` | "triage network", "triage ci failure", "run triager", "scan network issues" | Triage bugs, CI failures, and GitHub issues for network collections. Includes 6 known CI patterns, cross-collection cascade detection, and ansible-network-triager integration. |

## Architecture

These skills do NOT duplicate harness logic. They **extend** base harness skills using the `requires` field:

```
aap-sdlc-harness (generic)
  ├── triage-workflow          ← base triage logic (severity, Jira, duplicates)
  └── test-unit-workflow       ← base test logic

content-networking (this repo)
  ├── network-triage-workflow  ← requires: triage-workflow
  │                               adds: 6 CI patterns, severity escalators,
  │                               triager integration, cascade detection
  └── (more skills coming)
```

When `network-triage-workflow` loads, the system also loads `triage-workflow` from harness into the same context. Our skill says "follow the base steps, but check these patterns first and apply these networking-specific rules."

## Collections Covered

cisco.ios, cisco.iosxr, cisco.nxos, arista.eos, junipernetworks.junos, cisco.asa, vyos.vyos, ansible.netcommon, ansible.utils

## Related Tools

- [ansible-network-triager](https://github.com/ansible-network/ansible-network-triager) — Python CLI that scans GitHub for unassigned issues and CI failures across network collection repos. The triage skill integrates with it via `triager-json.py`.

## Contributing

1. Create a new skill directory under `skills/`
2. Write a `SKILL.md` with frontmatter (name, description, version, requires, triggers)
3. If your skill extends a harness skill, add it to `requires`
4. Open a PR
