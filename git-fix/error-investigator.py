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
