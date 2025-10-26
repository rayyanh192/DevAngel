import json
import boto3
import urllib3
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = 'devangel-incident-data-1761448500'

# Replace with your Slack webhook URL
SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

def lambda_handler(event, context):
    """
    Fast updater with Slack notifications
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
    
    # Send Slack notification
    slack_result = send_slack_notification(incident_id, severity, total_errors, deploy_sha, source_output)
    
    return {
        'incident_id': incident_id,
        'update_type': 'initial',
        'stored': True,
        'slack_sent': slack_result
    }

def send_slack_notification(incident_id, severity, total_errors, deploy_sha, source_output):
    """Send Slack notification about the incident"""
    
    # Get severity color
    severity_colors = {
        'critical': '#e74c3c',
        'high': '#f39c12',
        'medium': '#f1c40f',
        'low': '#3498db'
    }
    
    color = severity_colors.get(severity, '#f1c40f')
    
    # Create error timeline summary
    timeline = source_output.get('series', [])
    timeline_text = ', '.join([f"{point[0]}: {point[1]} errors" for point in timeline[:3]])
    
    # Create Slack message
    slack_message = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"DevAngel Incident Alert - {severity.upper()}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Incident ID:*\n{incident_id}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Total Errors:*\n{total_errors}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Deploy SHA:*\n{deploy_sha}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Severity:*\n{severity.upper()}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Error Timeline:*\n{timeline_text}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*AI Analysis in progress...* Full report will be available shortly."
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Dashboard"
                                },
                                "url": "https://your-amplify-dashboard-url.com",
                                "style": "primary"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    try:
        http = urllib3.PoolManager()
        response = http.request(
            'POST',
            SLACK_WEBHOOK_URL,
            body=json.dumps(slack_message),
            headers={'Content-Type': 'application/json'}
        )
        return {'status': 'sent', 'response_code': response.status}
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
