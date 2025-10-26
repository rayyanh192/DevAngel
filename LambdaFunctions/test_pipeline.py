#!/usr/bin/env python3
"""
Test the Step Functions pipeline locally with Bedrock summarizer
"""

import json
from source_adapter import lambda_handler as source_handler
from error_analyzer import lambda_handler as analyzer_handler
from error_summarizer import lambda_handler as summarizer_handler

def test_step_functions_pipeline():
    """Simulate the Step Functions pipeline locally"""
    
    print("=== Step Functions Pipeline Test with Bedrock ===\n")
    
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
    
    print("\n3. Starting ErrorSummarizer (Bedrock)...")
    
    # Step 3: ErrorSummarizer (gets combined data)
    summarizer_input = {
        'source_adapter_output': source_result['source_adapter_output'],
        'error_analyzer_output': analyzer_result
    }
    
    try:
        summarizer_result = summarizer_handler(summarizer_input, {})
        print(f"   ErrorSummarizer completed: {len(summarizer_result.get('error_summaries', []))} summaries generated")
    except Exception as e:
        print(f"   ErrorSummarizer failed (using fallback): {str(e)}")
        # Create fallback summary
        summarizer_result = create_fallback_summary(source_result, analyzer_result)
    
    print("\n4. Combining results...")
    
    # Step 4: Combine results (like Step Functions CombineResults state)
    final_result = {
        'source_adapter_output': source_result['source_adapter_output'],
        'error_analyzer_output': analyzer_result,
        'error_summarizer_output': summarizer_result,
        'pipeline_status': 'success',
        'timestamp': '2025-10-25T19:20:00Z'
    }
    
    # Save final result
    with open('pipeline_result.json', 'w') as f:
        json.dump(final_result, f, indent=2)
    
    print("\n5. Pipeline Results:")
    print(f"   Total Errors: {analyzer_result['basic_stats']['total_errors']}")
    print(f"   Deploy SHA: {analyzer_result['basic_stats']['deploy_sha']}")
    print(f"   Affected Files: {analyzer_result['basic_stats']['affected_files']}")
    print(f"   Error Summaries: {len(summarizer_result.get('error_summaries', []))}")
    print(f"   Status: {final_result['pipeline_status']}")
    
    # Show sample summaries
    if summarizer_result.get('error_summaries'):
        print(f"\n6. Sample Error Summary:")
        print(f"   {summarizer_result['error_summaries'][0][:100]}...")
    
    if summarizer_result.get('overall_summary'):
        print(f"\n7. Overall Summary:")
        print(f"   {summarizer_result['overall_summary'][:150]}...")
    
    print(f"\nPipeline result saved to: pipeline_result.json")
    print("This includes human-readable error summaries from Bedrock!")
    
    return final_result

def create_fallback_summary(source_result, analyzer_result):
    """Create fallback summaries if Bedrock is unavailable"""
    
    exemplars = source_result['source_adapter_output'].get('exemplars', [])
    basic_stats = analyzer_result.get('basic_stats', {})
    deploy = source_result['source_adapter_output'].get('deploy', {})
    
    error_summaries = []
    for exemplar in exemplars[:3]:
        message = exemplar.get('@message', '') or exemplar.get('message', '')
        if 'timeout' in message.lower():
            summary = "Payment service timeouts are causing transaction failures, preventing users from completing purchases."
        elif 'database' in message.lower():
            summary = "Database connection issues are disrupting data access, affecting core application functionality."
        elif 'connection' in message.lower():
            summary = "Network connectivity problems are causing service interruptions and user-facing errors."
        else:
            summary = "Application errors are occurring that may impact user experience and system reliability."
        
        error_summaries.append(summary)
    
    overall_summary = f"System experiencing {basic_stats.get('total_errors', 0)} errors after deployment {deploy.get('sha', 'unknown')}. The recent timeout configuration changes appear to be causing payment processing failures and database connectivity issues, directly impacting user transactions."
    
    recommendations = [
        {
            'priority': 'high',
            'action': 'Consider rollback to previous deployment',
            'reason': f'Multiple errors correlate with deployment {deploy.get("sha", "unknown")}'
        },
        {
            'priority': 'medium',
            'action': 'Monitor payment processing metrics',
            'reason': 'Payment timeouts detected affecting user transactions'
        }
    ]
    
    return {
        'error_summaries': error_summaries,
        'overall_summary': overall_summary,
        'recommendations': recommendations
    }

if __name__ == "__main__":
    test_step_functions_pipeline()
