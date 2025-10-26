# import json, os, urllib.request, urllib.error

# OWNER = os.getenv("GITHUB_OWNER")
# REPO  = os.getenv("GITHUB_REPO")
# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# Q_LABEL = "Amazon Q development agent"

# def gh_post(url, payload, timeout=15):
#     data = json.dumps(payload).encode("utf-8")
#     req = urllib.request.Request(
#         url, data=data, method="POST",
#         headers={
#             "Authorization": f"Bearer {GITHUB_TOKEN}",
#             "Accept": "application/vnd.github+json",
#             "Content-Type": "application/json"
#         }
#     )
#     with urllib.request.urlopen(req, timeout=timeout) as resp:
#         return resp.getcode(), json.loads(resp.read().decode("utf-8"))

# def lambda_handler(event, context):
#     incident_time = event.get("incident_time", "unknown")
#     likely_files = event.get("likely_files", [])
#     error_json = event.get("error_json", {})

#     body = (
#         "[QuietOps] Automated incident\n\n"
#         f"Time: {incident_time}\n"
#         f"Likely files: {likely_files}\n\n"
#         "Cleaned errors:\n```json\n"
#         f"{json.dumps(error_json, indent=2)}\n"
#         "```\n\nPlease create a minimal fix and open a Draft PR against `main`."
#     )

#     # ensure label exists (idempotent)
#     try:
#         gh_post(f"https://api.github.com/repos/{OWNER}/{REPO}/labels",
#                 {"name": Q_LABEL, "color": "1f883d"}, timeout=10)
#     except Exception:
#         pass  # label may already exist

#     # create issue (triggers Q)
#     status, issue = gh_post(
#         f"https://api.github.com/repos/{OWNER}/{REPO}/issues",
#         {"title": "[QuietOps] Fix errors after deploy", "body": body, "labels": [Q_LABEL]},
#         timeout=15
#     )
#     if status >= 300:
#         raise Exception(f"GitHub issue create failed: {status} {issue}")
#     return {"issue_url": issue["html_url"], "issue_number": issue["number"]}

import json, os, urllib.request, urllib.error

OWNER = os.getenv("GITHUB_OWNER")
REPO  = os.getenv("GITHUB_REPO")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
Q_LABEL = "Amazon Q development agent"
UA = "quietops-lambda/1.0"

def gh_post(url, payload, timeout=15):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": UA
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise Exception(f"GitHub HTTP {e.code}: {body}")

def gh_get(url, timeout=10):
    req = urllib.request.Request(
        url, headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": UA
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.getcode(), json.loads(resp.read().decode("utf-8"))

def lambda_handler(event, context):
    # sanity check token
    code, me = gh_get("https://api.github.com/user")
    if code != 200:
        raise Exception(f"Token unusable: HTTP {code} {me}")

    incident_time = event.get("incident_time", "unknown")
    likely_files = event.get("likely_files", [])
    error_json = event.get("error_json", {})

    body = (
        "[QuietOps] Automated incident\n\n"
        f"Time: {incident_time}\n"
        f"Likely files: {likely_files}\n\n"
        "Cleaned errors:\n```json\n"
        f"{json.dumps(error_json, indent=2)}\n"
        "```\n\nPlease create a minimal fix and open a Draft PR against `main`."
    )

    # ensure label exists (ignore if already there)
    try:
        gh_post(f"https://api.github.com/repos/{OWNER}/{REPO}/labels",
                {"name": Q_LABEL, "color": "1f883d"})
    except Exception:
        pass

    # create issue (triggers Q)
    status, issue = gh_post(
        f"https://api.github.com/repos/{OWNER}/{REPO}/issues",
        {"title": "[QuietOps] Fix errors after deploy", "body": body, "labels": [Q_LABEL]}
    )
    return {"issue_url": issue["html_url"], "issue_number": issue["number"]}