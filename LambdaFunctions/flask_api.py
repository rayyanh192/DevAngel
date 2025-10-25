from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from error_analyzer import lambda_handler

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

@app.route('/analyze-errors', methods=['POST'])
def analyze_errors():
    """
    API endpoint to analyze errors from SourceAdapter output
    Expects JSON payload with SourceAdapter format
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Process with ErrorAnalyzer
        result = lambda_handler(data, {})
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test', methods=['GET'])
def test_with_sample():
    """
    Test endpoint using the cloudwatch_response.json file
    """
    try:
        # Load sample data
        with open('cloudwatch_response.json', 'r') as f:
            sample_data = json.load(f)
        
        # Process with ErrorAnalyzer
        result = lambda_handler(sample_data, {})
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'error-analyzer-api'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
