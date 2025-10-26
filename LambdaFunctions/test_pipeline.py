#!/usr/bin/env python3
"""
Test the Step Functions pipeline locally
"""

import json
from source_adapter import lambda_handler as source_handler
from error_analyzer import lambda_handler as analyzer_handler

def test_step_functions_pipeline():
    """Simulate the Step Functions pipeline locally"""
    
    print("=== Step Functions Pipeline Test ===\n")
    
    # Load test data
    with open('cloudwatch_test.json', 'r') as f:
        input_data = json.load(f)
    
    print("1. Starting SourceAdapter...")
    
    # Step 1: SourceAdapter
    source_result = source_handler(input_data, {})
    print(f"   SourceAdapter completed: {len(source_result['source_adapter_output']['series'])} time points")
    
    print("\n2. Starting ErrorAnalyzer...")
    
    # Step 2: ErrorAnalyzer (gets SourceAdapter output)
    analyzer_input = source_result['source_adapter_output']
    analyzer_result = analyzer_handler(analyzer_input, {})
    print(f"   ErrorAnalyzer completed: {analyzer_result['status']}")
    
    print("\n3. Combining results...")
    
    # Step 3: Combine results (like Step Functions CombineResults state)
    final_result = {
        'source_adapter_output': source_result['source_adapter_output'],
        'error_analyzer_output': analyzer_result,
        'pipeline_status': 'success',
        'timestamp': '2025-10-25T17:35:00Z'
    }
    
    # Save final result
    with open('pipeline_result.json', 'w') as f:
        json.dump(final_result, f, indent=2)
    
    print("\n4. Pipeline Results:")
    print(f"   Total Errors: {analyzer_result['basic_stats']['total_errors']}")
    print(f"   Deploy SHA: {analyzer_result['basic_stats']['deploy_sha']}")
    print(f"   Affected Files: {analyzer_result['basic_stats']['affected_files']}")
    print(f"   Status: {final_result['pipeline_status']}")
    
    print(f"\nPipeline result saved to: pipeline_result.json")
    print("This simulates what Step Functions would produce!")
    
    return final_result

if __name__ == "__main__":
    test_step_functions_pipeline()
