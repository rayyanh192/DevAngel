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
    Enhanced updater with Slack completion notification
    """
    
    source_output = event.get('source_adapter_output', {})
    analyzer_output = event.get('error_analyzer_output', {})
    summarizer_output = event.get('error_summarizer_output', {})
    
    incident_id = f"incident-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    enhanced_data = {
        'incident_id': incident_id,
        'timestamp': datetime.now().isoformat(),
        'status': determine_severity(analyzer_output),
        'update_type': 'enhanced',
        'summary': {
            'total_errors': analyzer_output.get('basic_stats', {}).get('total_errors', 0),
            'deploy_sha': analyzer_output.get('basic_stats', {}).get('deploy_sha'),
            'deploy_message': analyzer_output.get('basic_stats', {}).get('deploy_message'),
            'affected_files': analyzer_output.get('basic_stats', {}).get('affected_files', 0)
        },
        'timeline': {
            'error_series': source_output.get('series', []),
            'deploy_correlation': summarizer_output.get('timeline_analysis', {})
        },
        'charts': {
            'error_timeline': source_output.get('series', []),
            'file_impact': source_output.get('file_hits', {}),
            'top_errors': analyzer_output.get('dashboard_ready', {}).get('top_errors', [])[:5]
        },
        'analysis': {
            'status': 'Complete',
            'executive_summary': summarizer_output.get('detailed_analysis', ''),
            'recommendations': summarizer_output.get('recommendations', [])
        }
    }
    
    # Store enhanced data in S3
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=f'incidents/{incident_id}-enhanced.json',
        Body=json.dumps(enhanced_data),
        ContentType='application/json',
        Metadata={'update-type': 'enhanced', 'incident-id': incident_id}
    )
    
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key='latest-incident.json',
        Body=json.dumps(enhanced_data),
        ContentType='application/json'
    )
    
    # Send Slack completion notification
    slack_result = send_completion_notification(enhanced_data, summarizer_output)
    
    return {
        'incident_id': incident_id,
        'update_type': 'enhanced',
        'stored': True,
        'slack_sent': slack_result
    }

def send_completion_notification(enhanced_data, summarizer_output):
    """Send Slack notification when AI analysis is complete"""
    
    incident_id = enhanced_data['incident_id']
    recommendations = summarizer_output.get('recommendations', [])
    timeline_analysis = summarizer_output.get('timeline_analysis', {})
    
    # Get top recommendation
    top_rec = recommendations[0] if recommendations else None
    
    # Create completion message
    slack_message = {
        "attachments": [
            {
                "color": "#27ae60",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "DevAngel Analysis Complete"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Incident:* {incident_id}\n*Status:* Analysis completed with AI recommendations"
                        }
                    }
                ]
            }
        ]
    }
    
    # Add deployment correlation if available
    if timeline_analysis.get('deploy_impact'):
        deploy_info = {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Deploy Correlation:*\n{timeline_analysis.get('correlation', 'unknown').upper()}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Time After Deploy:*\n{timeline_analysis.get('minutes_after_deploy', 'unknown')} minutes"
                }
            ]
        }
        slack_message["attachments"][0]["blocks"].append(deploy_info)
    
    # Add top recommendation
    if top_rec:
        rec_section = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Top Recommendation ({top_rec.get('priority', 'MEDIUM')}):*\n{top_rec.get('action', 'No specific action')}\n\n*Reason:* {top_rec.get('reason', 'Analysis complete')}"
            }
        }
        slack_message["attachments"][0]["blocks"].append(rec_section)
    
    # Add action buttons
    actions = {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "View Full Analysis"
                },
                "url": "https://your-amplify-dashboard-url.com",
                "style": "primary"
            }
        ]
    }
    
    # Add rollback button if recommended
    if any(rec.get('priority') == 'CRITICAL' for rec in recommendations):
        actions["elements"].append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Consider Rollback"
            },
            "style": "danger"
        })
    
    slack_message["attachments"][0]["blocks"].append(actions)
    
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
