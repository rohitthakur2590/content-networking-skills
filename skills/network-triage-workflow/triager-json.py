#!/usr/bin/env python3
"""JSON wrapper for ansible-network-triager.

The triager tool outputs prettytable text. This wrapper calls the same
Python API and produces structured JSON — easier for skills to parse.

Usage:
    python triager-json.py --bugs --triager-path /path/to/ansible-network-triager
    python triager-json.py --ci --triager-path /path/to/ansible-network-triager
    python triager-json.py --bugs  # uses TRIAGER_PATH env var or sibling dir
"""

import argparse
import json
import os
import sys
from datetime import datetime


def find_triager_path(explicit_path=None):
    """Resolve the triager install path."""
    if explicit_path:
        return explicit_path

    # Check env var
    env_path = os.environ.get("TRIAGER_PATH")
    if env_path and os.path.isdir(env_path):
        return env_path

    # Check sibling directory (common local dev layout)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sibling = os.path.normpath(
        os.path.join(script_dir, "..", "..", "..", "ansible-network-triager")
    )
    if os.path.isdir(sibling):
        return sibling

    return None


def run_bugs(config_path, triager_path):
    """Run bug triage and return structured JSON."""
    sys.path.insert(0, triager_path)

    try:
        from triager.config import Config
        from triager.triager import triage
    except ImportError as e:
        return {
            "error": True,
            "message": f"Cannot import triager modules: {e}",
            "help": (
                "Install the triager: cd /path/to/ansible-network-triager && pip install -e ."
            ),
        }

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv is optional

    config = Config(config_path)
    issues = triage(config, config.bug_repos)

    # Structure the output
    result = {
        "mode": "bugs",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "since_days": int(config.config_data.get("timedelta", 14)),
        "repos": {},
        "summary": {
            "total_items": 0,
            "by_repo": {},
            "by_type": {"Pull Request": 0, "Issue": 0},
        },
    }

    for repo_name, items in issues.items():
        result["repos"][repo_name] = items
        result["summary"]["by_repo"][repo_name] = len(items)
        result["summary"]["total_items"] += len(items)
        for item in items:
            item_type = item.get("type", "Issue")
            result["summary"]["by_type"][item_type] = (
                result["summary"]["by_type"].get(item_type, 0) + 1
            )

    return result


def run_ci(config_path, triager_path):
    """Run CI report and return structured JSON."""
    sys.path.insert(0, triager_path)

    try:
        from triager.ci_report import generate_ci_report
        from triager.config import Config
    except ImportError as e:
        return {
            "error": True,
            "message": f"Cannot import triager modules: {e}",
            "help": (
                "Install the triager: cd /path/to/ansible-network-triager && pip install -e ."
            ),
        }

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    config = Config(config_path)
    report = generate_ci_report(config)

    if not report:
        return {
            "mode": "ci",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "error": True,
            "message": "No CI report generated",
        }

    result = {
        "mode": "ci",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "overall_status": report.get("overall_status", "Unknown"),
        "repos": [],
        "summary": {
            "total_repos": len(report.get("data", [])),
            "passing": 0,
            "failing": 0,
        },
    }

    for entry in report.get("data", []):
        result["repos"].append(entry)
        if entry.get("status") == "success":
            result["summary"]["passing"] += 1
        else:
            result["summary"]["failing"] += 1

    return result


def main():
    parser = argparse.ArgumentParser(
        description="JSON wrapper for ansible-network-triager"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bugs", action="store_true", help="Run bug scrub")
    group.add_argument("--ci", action="store_true", help="Run CI report")

    parser.add_argument(
        "--triager-path",
        help="Path to ansible-network-triager repo (or set TRIAGER_PATH env var)",
    )
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="Path to config.yaml (defaults to triager repo's config.yaml)",
    )

    args = parser.parse_args()

    triager_path = find_triager_path(args.triager_path)
    if not triager_path:
        print(json.dumps({
            "error": True,
            "message": "Cannot find ansible-network-triager",
            "help": "Set --triager-path or TRIAGER_PATH env var",
        }, indent=2))
        sys.exit(1)

    config_path = args.config or os.path.join(triager_path, "config.yaml")

    if args.bugs:
        result = run_bugs(config_path, triager_path)
    else:
        result = run_ci(config_path, triager_path)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
