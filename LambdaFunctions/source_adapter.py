import json
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter

#lambda handler
def lambda_handler(event, context):
    source = event.get('source', 'json')
    incident_input = event.get('incident_input', {})
    
    logs = incident_input.get('logs', [])
    deploy = incident_input.get('deploy', {})
    
    # Generate errors-per-minute time series
    series = generate_error_series(logs)
    
    # Extract exemplars (representative error lines)
    exemplars = extract_exemplars(logs)
    
    # Count file hits from stack traces
    file_hits = count_file_hits(logs)
    
    return {
        'series': series,
        'exemplars': exemplars,
        'file_hits': file_hits,
        'deploy': deploy
    }

def generate_error_series(logs):
    """Generate errors-per-minute time series"""
    error_counts = defaultdict(int)
    
    for log in logs:
        if is_error_log(log):
            timestamp = extract_timestamp(log)
            if timestamp:
                minute_key = timestamp.strftime('%Y-%m-%d %H:%M')
                error_counts[minute_key] += 1
    
    # Convert to sorted list of [timestamp, count] pairs
    series = [[k, v] for k, v in sorted(error_counts.items())]
    return series

def extract_exemplars(logs, max_exemplars=10):
    """Extract representative error lines"""
    error_logs = [log for log in logs if is_error_log(log)]
    
    # Group similar errors and pick representatives
    error_groups = defaultdict(list)
    
    for log in error_logs:
        error_signature = get_error_signature(log)
        error_groups[error_signature].append(log)
    
    exemplars = []
    for signature, group in error_groups.items():
        # Take the first occurrence of each error type
        exemplars.append(group[0])
        if len(exemplars) >= max_exemplars:
            break
    
    return exemplars[:max_exemplars]

def count_file_hits(logs):
    """Count files mentioned in stack traces"""
    file_counter = Counter()
    
    for log in logs:
        files = extract_files_from_stacktrace(log)
        for file_path in files:
            file_counter[file_path] += 1
    
    return dict(file_counter)

def is_error_log(log):
    """Check if log entry indicates an error"""
    if isinstance(log, dict):
        level = log.get('level', '').lower()
        # Handle CloudWatch @message and regular message fields
        message = (log.get('@message') or log.get('message', '')).lower()
        return level in ['error', 'fatal'] or 'error' in message or 'exception' in message or 'traceback' in message
    
    if isinstance(log, str):
        log_lower = log.lower()
        return any(keyword in log_lower for keyword in ['error', 'exception', 'fatal', 'traceback'])
    
    return False

def extract_timestamp(log):
    """Extract timestamp from log entry"""
    if isinstance(log, dict):
        # Handle CloudWatch format (@timestamp) and other formats
        timestamp_str = log.get('@timestamp') or log.get('timestamp') or log.get('ts') or log.get('time')
        if timestamp_str:
            try:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                pass
    
    if isinstance(log, str):
        # Try to extract ISO timestamp from string
        iso_pattern = r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'
        match = re.search(iso_pattern, log)
        if match:
            try:
                return datetime.fromisoformat(match.group().replace(' ', 'T'))
            except:
                pass
    
    return datetime.now()  # Fallback to current time

def get_error_signature(log):
    """Generate a signature for grouping similar errors"""
    if isinstance(log, dict):
        # Handle CloudWatch @message and regular message fields
        message = log.get('@message') or log.get('message', '')
    else:
        message = str(log)
    
    # Remove dynamic parts like timestamps, IDs, numbers
    signature = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '[TIMESTAMP]', message)
    signature = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '[UUID]', signature)
    signature = re.sub(r'\b\d+\b', '[NUMBER]', signature)
    
    return signature[:200]  # Truncate for grouping

def extract_files_from_stacktrace(log):
    """Extract file paths from stack traces"""
    files = []
    
    if isinstance(log, dict):
        # Handle CloudWatch @message and regular message/stacktrace fields
        message = log.get('@message', '')
        stacktrace = log.get('stacktrace', '')
        text = message + ' ' + stacktrace
    else:
        text = str(log)
    
    # Common file path patterns
    patterns = [
        r'at\s+[\w.]+\(([^:]+\.(?:py|js|java|rb|php|go|rs|cpp|c|h)):\d+\)',
        r'File\s+"([^"]+\.(?:py|js|java|rb|php|go|rs|cpp|c|h))"',
        r'([/\w.-]+\.(?:py|js|java|rb|php|go|rs|cpp|c|h)):\d+',
        r'at\s+([/\w.-]+\.(?:py|js|java|rb|php|go|rs|cpp|c|h)):\d+',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        files.extend(matches)
    
    return list(set(files))  # Remove duplicates
