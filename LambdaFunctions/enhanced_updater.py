import json
import boto3
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = 'devangel-incident-data-1761448500'

def lambda_handler(event, context):
    """
    Enhanced updater - stores complete incident data with Bedrock analysis
    """
    
    # Get all the data from the parallel branch
    source_output = event.get('source_adapter_output', {})
    analyzer_output = event.get('error_analyzer_output', {})
    summarizer_output = event.get('error_summarizer_output', {})
    
    # Get incident ID from the fast update (or create new one)
    incident_id = f"incident-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Create complete dashboard data with Bedrock analysis
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
    
    # Store enhanced data in S3 (this triggers second EventBridge)
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=f'incidents/{incident_id}-enhanced.json',
        Body=json.dumps(enhanced_data),
        ContentType='application/json',
        Metadata={'update-type': 'enhanced', 'incident-id': incident_id}
    )
    
    # Update latest with complete data
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key='latest-incident.json',
        Body=json.dumps(enhanced_data),
        ContentType='application/json'
    )
    
    return {
        'incident_id': incident_id,
        'update_type': 'enhanced',
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
