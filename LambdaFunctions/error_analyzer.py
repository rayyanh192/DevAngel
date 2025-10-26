import json

def lambda_handler(event, context):
    series = event.get('series', [])
    exemplars = event.get('exemplars', [])
    file_hits = event.get('file_hits', {})
    deploy = event.get('deploy', {})
    
    return {
        'status': 'success',
        'basic_stats': {
            'total_errors': sum(point[1] for point in series) if series else 0,
            'total_error_points': len(series),
            'unique_exemplars': len(exemplars),
            'affected_files': len(file_hits),
            'deploy_sha': deploy.get('sha'),
            'deploy_message': deploy.get('message')
        },
        'dashboard_ready': {
            'error_timeline': series,
            'top_errors': exemplars[:5],
            'file_impact': file_hits,
            'deployment_info': deploy
        }
    }
