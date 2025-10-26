import json
import re
from datetime import datetime
from collections import defaultdict, Counter

def lambda_handler(event, context):
    source = event.get('source', 'json')
    incident_input = event.get('incident_input', {})
    
    logs = incident_input.get('logs', [])
    deploy = incident_input.get('deploy', {})
    
    # Generate analysis
    series = generate_error_series(logs)
    exemplars = extract_exemplars(logs)
    file_hits = count_file_hits(logs)
    
    # Return output for Step Functions
    return {
        'source_adapter_output': {
            'series': series,
            'exemplars': exemplars,
            'file_hits': file_hits,
            'deploy': deploy
        }
    }

def generate_error_series(logs):
    error_counts = defaultdict(int)
    for log in logs:
        if is_error_log(log):
            timestamp = extract_timestamp(log)
            if timestamp:
                minute_key = timestamp.strftime('%Y-%m-%d %H:%M')
                error_counts[minute_key] += 1
    return [[k, v] for k, v in sorted(error_counts.items())]

def extract_exemplars(logs, max_exemplars=10):
    error_logs = [log for log in logs if is_error_log(log)]
    error_groups = defaultdict(list)
    for log in error_logs:
        error_signature = get_error_signature(log)
        error_groups[error_signature].append(log)
    exemplars = []
    for signature, group in error_groups.items():
        exemplars.append(group[0])
        if len(exemplars) >= max_exemplars:
            break
    return exemplars[:max_exemplars]

def count_file_hits(logs):
    file_counter = Counter()
    for log in logs:
        files = extract_files_from_stacktrace(log)
        for file_path in files:
            file_counter[file_path] += 1
    return dict(file_counter)

def is_error_log(log):
    if isinstance(log, dict):
        level = log.get('level', '').lower()
        message = (log.get('@message') or log.get('message', '')).lower()
        return level in ['error', 'fatal'] or 'error' in message or 'exception' in message or 'traceback' in message
    if isinstance(log, str):
        log_lower = log.lower()
        return any(keyword in log_lower for keyword in ['error', 'exception', 'fatal', 'traceback'])
    return False

def extract_timestamp(log):
    if isinstance(log, dict):
        timestamp_str = log.get('@timestamp') or log.get('timestamp') or log.get('ts') or log.get('time')
        if timestamp_str:
            try:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                pass
    if isinstance(log, str):
        iso_pattern = r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'
        match = re.search(iso_pattern, log)
        if match:
            try:
                return datetime.fromisoformat(match.group().replace(' ', 'T'))
            except:
                pass
    return datetime.now()

def get_error_signature(log):
    if isinstance(log, dict):
        message = log.get('@message') or log.get('message', '')
    else:
        message = str(log)
    signature = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '[TIMESTAMP]', message)
    signature = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '[UUID]', signature)
    signature = re.sub(r'\b\d+\b', '[NUMBER]', signature)
    return signature[:200]

def extract_files_from_stacktrace(log):
    files = []
    if isinstance(log, dict):
        message = log.get('@message', '')
        stacktrace = log.get('stacktrace', '')
        text = message + ' ' + stacktrace
    else:
        text = str(log)
    patterns = [
        r'at\s+[\w.]+\(([^:]+\.(?:py|js|java|rb|php|go|rs|cpp|c|h)):\d+\)',
        r'File\s+"([^"]+\.(?:py|js|java|rb|php|go|rs|cpp|c|h))"',
        r'([/\w.-]+\.(?:py|js|java|rb|php|go|rs|cpp|c|h)):\d+',
        r'at\s+([/\w.-]+\.(?:py|js|java|rb|php|go|rs|cpp|c|h)):\d+',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        files.extend(matches)
    return list(set(files))
