import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')
sns = boto3.client('sns')
BUCKET_NAME = 'devangel-incident-data-1761448500'

# Replace with your phone number (format: +1234567890)
YOUR_PHONE_NUMBER = '+19084325309'

def lambda_handler(event, context):
    """
    Fast updater with SMS notification
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
    
    # Send SMS notification
    sms_result = send_sms_alert(incident_id, severity, total_errors, deploy_sha)
    
    return {
        'incident_id': incident_id,
        'update_type': 'initial',
        'stored': True,
        'sms_sent': sms_result
    }

def send_sms_alert(incident_id, severity, total_errors, deploy_sha):
    """Send SMS alert about the incident"""
    
    # Create SMS message (160 char limit)
    message = f"DevAngel Alert - {severity.upper()}\n{total_errors} errors detected\nDeploy: {deploy_sha}\nIncident: {incident_id}\nCheck dashboard for details."
    
    try:
        response = sns.publish(
            PhoneNumber=YOUR_PHONE_NUMBER,
            Message=message,
            Subject='DevAngel Incident Alert'
        )
        
        return {
            'status': 'sent',
            'message_id': response['MessageId']
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e)
        }

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
