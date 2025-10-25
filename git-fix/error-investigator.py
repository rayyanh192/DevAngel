import boto3
import requests
import json
from datetime import datetime, timedelta

def investigate_error_spike():
    # 1. Query CloudWatch Logs for recent errors
    logs_client = boto3.client('logs')
    
    # Get logs from the last 15 minutes
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=15)
    
    query = """
    fields @timestamp, @message
    | filter @message like /ERROR/
    | sort @timestamp desc
    | limit 20
    """
    
    response = logs_client.start_query(
        logGroupName='/aws/ec2/application',
        startTime=int(start_time.timestamp()),
        endTime=int(end_time.timestamp()),
        queryString=query
    )
    
    # 2. Analyze the error patterns
    error_summary = analyze_errors(response)
    
    # 3. Fire repository_dispatch to GitHub
    trigger_github_workflow(error_summary)

def analyze_errors(logs_response):
    # Simple analysis - in reality, you'd use more sophisticated logic
    return {
        "error_type": "Database Connection Timeout",
        "affected_files": ["src/database.py", "src/models/user.py"],
        "error_count": 15,
        "sample_logs": ["ERROR: Connection timeout after 30s", "ERROR: Failed to connect to DB"]
    }


def trigger_github_workflow(error_data):
    github_token = "your_github_token"
    repo_owner = "your-username"
    repo_name = "your-repo"
    
    payload = {
        "event_type": "auto_fix_request",
        "client_payload": {
            "error_summary": error_data,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    response = requests.post(
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/dispatches",
        headers={
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        },
        json=payload
    )
    
    print(f"GitHub dispatch triggered: {response.status_code}")

if __name__ == "__main__":
    investigate_error_spike()

