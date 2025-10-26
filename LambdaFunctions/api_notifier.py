import json
import boto3
import urllib3

def lambda_handler(event, context):
    """
    Takes Step Functions output and sends it to the Dashboard API
    """
    
    # API endpoint
    api_url = 'https://6w7s9tmece.execute-api.us-east-1.amazonaws.com/prod/incidents'
    
    try:
        # Send Step Functions output to API
        http = urllib3.PoolManager()
        
        response = http.request(
            'POST',
            api_url,
            body=json.dumps(event),
            headers={'Content-Type': 'application/json'}
        )
        
        return {
            'statusCode': response.status,
            'api_response': response.data.decode('utf-8'),
            'notification_sent': True
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'error': str(e),
            'notification_sent': False
        }
