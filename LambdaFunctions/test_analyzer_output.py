#!/usr/bin/env python3
"""
Test script to work with ErrorAnalyzer output
"""

import json

def test_analyzer_output():
    """Test and demonstrate using ErrorAnalyzer output"""
    
    # Load the ErrorAnalyzer output
    with open('analyzer_output.json', 'r') as f:
        data = json.load(f)
    
    print("=== ErrorAnalyzer Output Test ===\n")
    
    # Test 1: Check if analysis was successful
    print("1. Analysis Status:")
    print(f"   Status: {data['status']}")
    print(f"   Valid Input: {data['input_validation']['valid']}")
    print(f"   Summary: {data['input_validation']['summary']}")
    
    # Test 2: Extract key metrics for dashboard
    print("\n2. Key Metrics for Dashboard:")
    stats = data['basic_stats']
    print(f"   Total Errors: {stats['total_errors']}")
    print(f"   Error Time Points: {stats['total_error_points']}")
    print(f"   Affected Files: {stats['affected_files']}")
    print(f"   Deploy SHA: {stats['deploy_info']['sha']}")
    print(f"   Files Changed: {stats['deploy_info']['files_changed']}")
    
    # Test 3: Preview data for quick insights
    print("\n3. Quick Insights:")
    preview = data['preview']
    print(f"   First Error Time: {preview['first_error_time']}")
    print(f"   Peak Errors: {preview['peak_errors']}")
    print(f"   Top Error: {preview['top_error_example']}")
    print(f"   Most Hit File: {preview['most_hit_file'][0]} ({preview['most_hit_file'][1]} times)")
    
    # Test 4: Create dashboard-ready JSON structure
    print("\n4. Dashboard-Ready JSON Structure:")
    dashboard_json = create_dashboard_json(data)
    print(json.dumps(dashboard_json, indent=2))
    
    return dashboard_json

def create_dashboard_json(analyzer_data):
    """Convert ErrorAnalyzer output to dashboard-friendly format"""
    
    stats = analyzer_data['basic_stats']
    preview = analyzer_data['preview']
    
    dashboard_data = {
        "summary": {
            "total_errors": stats['total_errors'],
            "time_points": stats['total_error_points'],
            "affected_files": stats['affected_files'],
            "status": "critical" if stats['total_errors'] > 5 else "warning" if stats['total_errors'] > 2 else "normal"
        },
        "deployment": {
            "sha": stats['deploy_info']['sha'],
            "message": stats['deploy_info']['message'],
            "files_changed": stats['deploy_info']['files_changed']
        },
        "timeline": {
            "first_error": preview['first_error_time'],
            "peak_errors": preview['peak_errors']
        },
        "top_issues": {
            "primary_error": preview['top_error_example'],
            "most_affected_file": preview['most_hit_file'][0],
            "file_hit_count": preview['most_hit_file'][1]
        },
        "alerts": [
            {
                "type": "error_spike",
                "message": f"Peak of {preview['peak_errors']} errors detected",
                "severity": "high" if preview['peak_errors'] > 3 else "medium"
            }
        ]
    }
    
    return dashboard_data

if __name__ == "__main__":
    result = test_analyzer_output()
    
    # Save dashboard JSON for frontend use
    with open('dashboard_data.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("Dashboard data saved to dashboard_data.json")
    print("This JSON is ready to be consumed by your frontend!")
