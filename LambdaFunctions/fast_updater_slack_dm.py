import json
import boto3
import urllib3
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = 'devangel-incident-data-1761448500'

# Replace with your Slack Bot Token (starts with xoxb-)
SLACK_BOT_TOKEN = 'xoxb-your-bot-token-here'
# Replace with your Slack User ID (starts with U)
YOUR_USER_ID = 'U1234567890'

def lambda_handler(event, context):
    """
    Fast updater with personal Slack DM
    """
    
    source_output = event.get('source_adapter_output', {})
    analyzer_output = event.get('error_analyzer_output', {})
    
    # Create fast dashboard data
    incident_id = f"incident-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    severity = determine_severity(analyzer_output)
    total_errors = analyzer_output.get('basic_stats', {}).get('total_errors', 0)
    deploy_sha = analyzer_output.get('basic_stats', {}).get('deploy_sha', 'unknown')
    
    fast_data = {
        'incident_id': incident_id,
        'timestamp': datetime.now().isoformat(),
        'status': severity,
        'update_type': 'initial',
        'summary': {
            'total_errors': total_errors,
            'deploy_sha': deploy_sha,
            'deploy_message': analyzer_output.get('basic_stats', {}).get('deploy_message'),
            'affected_files': analyzer_output.get('basic_stats', {}).get('affected_files', 0)
        },
        'charts': {
            'error_timeline': source_output.get('series', []),
            'file_impact': source_output.get('file_hits', {}),
            'top_errors': analyzer_output.get('dashboard_ready', {}).get('top_errors', [])[:5]
        },
        'analysis': {
            'status': 'Processing AI analysis...',
            'executive_summary': 'Incident detected. AI analysis in progress...',
            'recommendations': [{
                'priority': 'HIGH',
                'action': 'Monitor system while analysis completes',
                'reason': 'Initial incident response'
            }]
        }
    }
    
    # Store in S3
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=f'incidents/{incident_id}-initial.json',
        Body=json.dumps(fast_data),
        ContentType='application/json',
        Metadata={'update-type': 'initial', 'incident-id': incident_id}
    )
    
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key='latest-incident.json',
        Body=json.dumps(fast_data),
        ContentType='application/json'
    )
    
    # Send personal Slack DM
    slack_result = send_personal_slack_dm(incident_id, severity, total_errors, deploy_sha, source_output)
    
    return {
        'incident_id': incident_id,
        'update_type': 'initial',
        'stored': True,
        'slack_sent': slack_result
    }

def send_personal_slack_dm(incident_id, severity, total_errors, deploy_sha, source_output):
    """Send personal Slack DM about the incident"""
    
    # Create error timeline summary
    timeline = source_output.get('series', [])
    timeline_text = ', '.join([f"{point[0]}: {point[1]} errors" for point in timeline[:3]])
    
    # Create message text
    message_text = f"""*DevAngel Alert - {severity.upper()}*

*Incident:* {incident_id}
*Total Errors:* {total_errors}
*Deploy SHA:* {deploy_sha}
*Timeline:* {timeline_text}

AI analysis in progress... Full report coming soon.
"""
    
    # Slack API payload
    slack_payload = {
        'channel': YOUR_USER_ID,
        'text': message_text,
        'as_user': True
    }
    
    try:
        http = urllib3.PoolManager()
        response = http.request(
            'POST',
            'https://slack.com/api/chat.postMessage',
            body=json.dumps(slack_payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {SLACK_BOT_TOKEN}'
            }
        )
        
        result = json.loads(response.data.decode('utf-8'))
        return {'status': 'sent' if result.get('ok') else 'failed', 'response': result}
        
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}

def determine_severity(analyzer_output):
    """Determine incident severity"""
    total_errors = analyzer_output.get('basic_stats', {}).get('total_errors', 0)
    
    if total_errors >= 10:
        return 'critical'
    elif total_errors >= 5:
        return 'high'
    elif total_errors >= 1:
        return 'medium'
    else:
        return 'low'
