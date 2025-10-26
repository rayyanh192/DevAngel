#!/usr/bin/env python3
"""
error-investigator.py

Read a cleaned JSON of errors (from a file or stdin), then either:
- trigger a GitHub repository_dispatch event (default), or
- optionally apply safe local 'suggestion' edits to affected files in a new git branch (--apply-local).

Usage examples:
  python error-investigator.py --json-file errors.json
  cat errors.json | python error-investigator.py
  python error-investigator.py --json-file errors.json --apply-local

Environment variables (preferred for automation):
  GITHUB_TOKEN   - token with repo:dispatch permissions
  REPO_OWNER     - GitHub repo owner (org or user)
  REPO_NAME      - GitHub repository name

"""

import argparse
import base64
import datetime
import gzip
import json
import os
import subprocess
import sys
from typing import Any, Dict

import requests


def load_json_input(path: str | None) -> Dict[str, Any]:
    """Load JSON from a file path or stdin. Returns the error summary dict.

    Accepts two shapes:
    - Full payload that has top-level key "error_summary" (e.g., {"error_summary": { ... }})
    - Direct summary object (e.g., {"error_type":..., "affected_files": [...], ...})
    """
    raw = None
    if path:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    if not raw:
        raise SystemExit("No JSON input provided (file was empty or no stdin).")

    data = json.loads(raw)
    if isinstance(data, dict) and "error_summary" in data:
        return data["error_summary"]
    return data


def validate_summary(summary: Dict[str, Any]) -> None:
    required = ["error_type", "affected_files", "error_count"]
    missing = [k for k in required if k not in summary]
    if missing:
        raise SystemExit(f"Invalid error summary: missing keys {missing}")


def trigger_github_workflow(summary: Dict[str, Any], owner: str, repo: str, token: str) -> None:
    if not token:
        raise SystemExit("GITHUB_TOKEN is required to trigger GitHub repository_dispatch")
    if not owner or not repo:
        raise SystemExit("REPO_OWNER and REPO_NAME are required to trigger GitHub repository_dispatch")

    payload = {
        "event_type": "auto_fix_request",
        "client_payload": {"error_summary": summary, "timestamp": datetime.datetime.utcnow().isoformat()}
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/dispatches"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code in (204, 202):
        print(f"GitHub dispatch sent (status {resp.status_code}) to {owner}/{repo}")
    else:
        print(f"GitHub dispatch failed: {resp.status_code} {resp.text}")
        resp.raise_for_status()


def run_cmd(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=capture, text=True)


def apply_local_suggestions(summary: Dict[str, Any], branch_prefix: str = "auto-fix") -> None:
    """Create a new git branch and insert suggestion comments into affected files, then commit.

    This is intentionally conservative: it will only modify files that already exist in the repo.
    """
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    branch = f"{branch_prefix}/{ts}"

    # Create branch
    print(f"Creating local branch: {branch}")
    run_cmd(["git", "checkout", "-b", branch])

    touched = []
    files = summary.get("affected_files") or []
    note = f"AUTO-FIX SUGGESTION: {summary.get('error_type')} (count={summary.get('error_count')})\nGenerated: {ts}\n"

    for fpath in files:
        if not os.path.exists(fpath):
            print(f"Skipping missing file: {fpath}")
            continue

        # Insert a header comment at the top of file with the suggestion
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                orig = fh.read()

            # Heuristic: decide comment prefix by file extension
            _, ext = os.path.splitext(fpath)
            if ext in (".py", ".sh", ".ini", ".cfg"):
                prefix = "# "
            elif ext in (".js", ".ts", ".java", ".c", ".cpp", ".go"):
                prefix = "// "
            else:
                prefix = "# "

            header = "".join(prefix + line + "\n" for line in note.splitlines()) + "\n"

            with open(fpath, "w", encoding="utf-8") as fh:
                fh.write(header + orig)

            run_cmd(["git", "add", fpath])
            touched.append(fpath)
            print(f"Inserted suggestion header into {fpath}")
        except Exception as e:
            print(f"Failed to modify {fpath}: {e}")

    if touched:
        commit_msg = f"Auto-fix suggestions: {summary.get('error_type')}"
        run_cmd(["git", "commit", "-m", commit_msg])
        run_cmd(["git", "push", "-u", "origin", branch])
        print(f"Pushed branch {branch} to origin")
    else:
        print("No files were modified; aborting commit.")


def main():
    parser = argparse.ArgumentParser(description="Process cleaned error JSON and dispatch or apply suggestions")
    parser.add_argument("--json-file", help="Path to JSON file with cleaned errors (or omit to read stdin)")
    parser.add_argument("--apply-local", action="store_true", help="Create a local git branch and insert suggestion headers into affected files")
    parser.add_argument("--repo-owner", help="GitHub repo owner (overrides REPO_OWNER env)")
    parser.add_argument("--repo-name", help="GitHub repo name (overrides REPO_NAME env)")
    parser.add_argument("--github-token", help="GitHub token (overrides GITHUB_TOKEN env)")

    args = parser.parse_args()

    summary = load_json_input(args.json_file)
    validate_summary(summary)

    # Resolve repo info
    owner = args.repo_owner or os.getenv("REPO_OWNER")
    repo = args.repo_name or os.getenv("REPO_NAME")
    token = args.github_token or os.getenv("GITHUB_TOKEN")

    # By default, trigger GitHub dispatch. If apply-local set, also do local edits.
    try:
        trigger_github_workflow(summary, owner, repo, token)
    except Exception as e:
        print(f"Warning: failed to trigger GitHub workflow: {e}")

    if args.apply_local:
        try:
            apply_local_suggestions(summary)
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

