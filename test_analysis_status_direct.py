#!/usr/bin/env python3
"""
Script to directly test the analysis_status endpoint on port 7001
to see what data structure is returned and if scores are included.
"""

import sys
import os
import json
import requests
from datetime import datetime

# Add the server directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import LlmResponse

def test_direct_analysis_status():
    """Test the analysis_status endpoint directly"""
    print("🔍 Testing Analysis Status Endpoint Directly")
    print("=" * 50)
    
    session = Session()
    
    try:
        # Get a recent task ID that was completed
        recent_response = session.query(LlmResponse).filter(
            LlmResponse.status == 'S',
            LlmResponse.task_id.isnot(None)
        ).order_by(LlmResponse.completed_processing_at.desc()).first()
        
        if not recent_response:
            print("❌ No recent completed responses with task_id found")
            return False
        
        task_id = recent_response.task_id
        print(f"📋 Testing with task ID: {task_id}")
        print(f"   Response ID: {recent_response.id}")
        print(f"   Completed: {recent_response.completed_processing_at}")
        
        # Make direct call to the service
        url = f"http://localhost:7001/analyze_status/{task_id}"
        print(f"🌐 Calling: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            print(f"📊 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ Successfully got JSON response")
                    print(f"📄 Response Keys: {list(data.keys())}")
                    
                    # Pretty print the full response
                    print(f"\n📋 Full Response:")
                    print(json.dumps(data, indent=2))
                    
                    # Look for score-related fields
                    score_fields = []
                    
                    def find_score_fields(obj, prefix=""):
                        """Recursively find fields that might contain scores"""
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                full_key = f"{prefix}.{key}" if prefix else key
                                if any(score_word in key.lower() for score_word in ['score', 'rating', 'confidence', 'probability']):
                                    score_fields.append((full_key, value))
                                elif isinstance(value, (dict, list)):
                                    find_score_fields(value, full_key)
                        elif isinstance(obj, list):
                            for idx, item in enumerate(obj):
                                find_score_fields(item, f"{prefix}[{idx}]")
                    
                    find_score_fields(data)
                    
                    if score_fields:
                        print(f"\n🎯 Score-related fields found:")
                        for field_name, field_value in score_fields:
                            print(f"   {field_name}: {field_value}")
                    else:
                        print(f"\n⚠️  No score-related fields found in response")
                    
                    # Check if results structure contains scores
                    if 'results' in data:
                        results = data['results']
                        print(f"\n📋 Results Analysis:")
                        print(f"   Number of results: {len(results) if isinstance(results, list) else 'Not a list'}")
                        
                        if isinstance(results, list) and results:
                            for i, result in enumerate(results):
                                print(f"\n   Result {i+1}:")
                                if isinstance(result, dict):
                                    print(f"      Keys: {list(result.keys())}")
                                    for key, value in result.items():
                                        if any(score_word in key.lower() for score_word in ['score', 'rating', 'confidence', 'probability']):
                                            print(f"      🎯 {key}: {value}")
                                        else:
                                            # Show first 100 chars of non-score fields
                                            value_str = str(value)
                                            if len(value_str) > 100:
                                                value_str = value_str[:100] + "..."
                                            print(f"      {key}: {value_str}")
                    
                    return True
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing JSON: {e}")
                    print(f"Raw response: {response.text[:500]}...")
                    return False
            
            elif response.status_code == 404:
                print(f"⚠️  Task not found (404) - this is expected for old tasks")
                print(f"Response: {response.text}")
                return True
            
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        session.close()

def test_with_multiple_task_ids():
    """Test with multiple recent task IDs to see different response patterns"""
    print("\n🔍 Testing Multiple Recent Task IDs")
    print("=" * 50)
    
    session = Session()
    
    try:
        # Get multiple recent task IDs
        recent_responses = session.query(LlmResponse).filter(
            LlmResponse.task_id.isnot(None)
        ).order_by(LlmResponse.completed_processing_at.desc()).limit(3).all()
        
        if not recent_responses:
            print("❌ No responses with task_id found")
            return False
        
        for i, response in enumerate(recent_responses, 1):
            print(f"\n📋 Test {i}: Task ID {response.task_id}")
            print(f"   Status: {response.status}")
            print(f"   Completed: {response.completed_processing_at}")
            
            url = f"http://localhost:7001/analyze_status/{response.task_id}"
            
            try:
                resp = requests.get(url, timeout=5)
                print(f"   HTTP Status: {resp.status_code}")
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        print(f"   Response Keys: {list(data.keys())}")
                        
                        # Quick check for scores
                        score_found = False
                        def check_for_scores(obj):
                            nonlocal score_found
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    if any(score_word in key.lower() for score_word in ['score', 'rating', 'confidence', 'probability']):
                                        score_found = True
                                        print(f"   🎯 Score field found: {key} = {value}")
                                    elif isinstance(value, (dict, list)):
                                        check_for_scores(value)
                            elif isinstance(obj, list):
                                for item in obj:
                                    check_for_scores(item)
                        
                        check_for_scores(data)
                        
                        if not score_found:
                            print(f"   ⚠️  No scores found")
                            
                    except json.JSONDecodeError:
                        print(f"   ❌ Invalid JSON response")
                        
                elif resp.status_code == 404:
                    print(f"   ⚠️  Task not found (expected for old tasks)")
                else:
                    print(f"   ❌ Error: {resp.text[:100]}...")
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Request failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        session.close()

if __name__ == "__main__":
    print("🔍 Direct Analysis Status Response Checker")
    print("=" * 60)
    
    # Test with a single task ID first
    success1 = test_direct_analysis_status()
    
    # Test with multiple task IDs
    success2 = test_with_multiple_task_ids()
    
    print("\n" + "=" * 60)
    if success1 or success2:
        print("✅ Testing completed - check output above for score data")
    else:
        print("❌ Testing failed")
