import json

def lambda_handler(event, context):
    """
    Part 1: Receive and validate SourceAdapter output
    """
    
    # Extract SourceAdapter output
    series = event.get('series', [])
    exemplars = event.get('exemplars', [])
    file_hits = event.get('file_hits', {})
    deploy = event.get('deploy', {})
    
    # Validate inputs
    validation_result = validate_inputs(series, exemplars, file_hits, deploy)
    
    if not validation_result['valid']:
        return {
            'error': 'Invalid input data',
            'details': validation_result['errors']
        }
    
    # Return validated data with basic stats
    return {
        'status': 'success',
        'input_validation': validation_result,
        'basic_stats': {
            'total_error_points': len(series),
            'total_errors': sum(point[1] for point in series) if series else 0,
            'unique_exemplars': len(exemplars),
            'affected_files': len(file_hits),
            'deploy_info': {
                'sha': deploy.get('sha'),
                'message': deploy.get('message'),
                'files_changed': len(deploy.get('changed_files', []))
            }
        },
        'preview': {
            'first_error_time': series[0][0] if series else None,
            'peak_errors': max(point[1] for point in series) if series else 0,
            'top_error_example': exemplars[0].get('@message', '')[:100] + '...' if exemplars else None,
            'most_hit_file': max(file_hits.items(), key=lambda x: x[1]) if file_hits else None
        }
    }

def validate_inputs(series, exemplars, file_hits, deploy):
    """Validate the SourceAdapter output format"""
    errors = []
    
    # Validate series format
    if not isinstance(series, list):
        errors.append("Series must be a list")
    else:
        for i, point in enumerate(series):
            if not isinstance(point, list) or len(point) != 2:
                errors.append(f"Series point {i} must be [timestamp, count]")
                break
            if not isinstance(point[1], (int, float)):
                errors.append(f"Series point {i} count must be a number")
                break
    
    # Validate exemplars
    if not isinstance(exemplars, list):
        errors.append("Exemplars must be a list")
    
    # Validate file_hits
    if not isinstance(file_hits, dict):
        errors.append("File_hits must be a dictionary")
    
    # Validate deploy
    if not isinstance(deploy, dict):
        errors.append("Deploy must be a dictionary")
    elif not deploy.get('sha'):
        errors.append("Deploy must have a 'sha' field")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'summary': f"Validated {len(series)} time points, {len(exemplars)} exemplars, {len(file_hits)} files"
    }
