import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = 'devangel-incident-data-1761448500'

def lambda_handler(event, context):
    """
    Fast updater - stores initial incident data for immediate dashboard update
    """
    
    source_output = event.get('source_adapter_output', {})
    analyzer_output = event.get('error_analyzer_output', {})
    
    # Create fast dashboard data (without Bedrock analysis)
    incident_id = f"incident-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    fast_data = {
        'incident_id': incident_id,
        'timestamp': datetime.now().isoformat(),
        'status': determine_severity(analyzer_output),
        'update_type': 'initial',
        'summary': {
            'total_errors': analyzer_output.get('basic_stats', {}).get('total_errors', 0),
            'deploy_sha': analyzer_output.get('basic_stats', {}).get('deploy_sha'),
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
    
    # Store initial data in S3 (this triggers EventBridge)
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=f'incidents/{incident_id}-initial.json',
        Body=json.dumps(fast_data),
        ContentType='application/json',
        Metadata={'update-type': 'initial', 'incident-id': incident_id}
    )
    
    # Also update latest for polling fallback
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key='latest-incident.json',
        Body=json.dumps(fast_data),
        ContentType='application/json'
    )
    
    return {
        'incident_id': incident_id,
        'update_type': 'initial',
        'stored': True
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
