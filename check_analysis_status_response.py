#!/usr/bin/env python3
"""
Script to check what data is being returned from analysis_status responses
and verify if scores are included in the response package.
"""

import sys
import os
import json
from datetime import datetime

# Add the server directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import LlmResponse

def check_recent_responses():
    """Check recent LLM responses to see what data is stored"""
    session = Session()
    
    try:
        print("🔍 Checking Recent LLM Response Data")
        print("=" * 50)
        
        # Get recent completed responses
        recent_responses = session.query(LlmResponse).filter(
            LlmResponse.status == 'S'  # Success status
        ).order_by(LlmResponse.completed_processing_at.desc()).limit(5).all()
        
        if not recent_responses:
            print("❌ No successful responses found")
            return False
        
        print(f"📊 Found {len(recent_responses)} recent successful responses")
        print()
        
        for i, response in enumerate(recent_responses, 1):
            print(f"🔸 Response {i} (ID: {response.id})")
            print(f"   Task ID: {response.task_id}")
            print(f"   Status: {response.status}")
            print(f"   Completed: {response.completed_processing_at}")
            print(f"   Response Time: {response.response_time_ms}ms")
            
            # Check response_json for score data
            if response.response_json:
                try:
                    response_data = json.loads(response.response_json)
                    print(f"   Response JSON Keys: {list(response_data.keys())}")
                    
                    # Look for score-related fields
                    score_fields = []
                    
                    def find_score_fields(data, prefix=""):
                        """Recursively find fields that might contain scores"""
                        if isinstance(data, dict):
                            for key, value in data.items():
                                full_key = f"{prefix}.{key}" if prefix else key
                                if any(score_word in key.lower() for score_word in ['score', 'rating', 'confidence', 'probability']):
                                    score_fields.append((full_key, value))
                                elif isinstance(value, (dict, list)):
                                    find_score_fields(value, full_key)
                        elif isinstance(data, list):
                            for idx, item in enumerate(data):
                                find_score_fields(item, f"{prefix}[{idx}]")
                    
                    find_score_fields(response_data)
                    
                    if score_fields:
                        print(f"   🎯 Score-related fields found:")
                        for field_name, field_value in score_fields:
                            print(f"      {field_name}: {field_value}")
                    else:
                        print(f"   ⚠️  No score-related fields found")
                    
                    # Show the structure of results if present
                    if 'results' in response_data:
                        results = response_data['results']
                        print(f"   📋 Results structure:")
                        if isinstance(results, list) and results:
                            first_result = results[0]
                            if isinstance(first_result, dict):
                                print(f"      Result keys: {list(first_result.keys())}")
                                # Check each result for scores
                                for j, result in enumerate(results):
                                    if isinstance(result, dict):
                                        result_scores = []
                                        for key, value in result.items():
                                            if any(score_word in key.lower() for score_word in ['score', 'rating', 'confidence', 'probability']):
                                                result_scores.append((key, value))
                                        if result_scores:
                                            print(f"      Result {j+1} scores: {result_scores}")
                    
                    # Show a sample of the actual JSON (truncated)
                    json_str = json.dumps(response_data, indent=2)
                    if len(json_str) > 500:
                        json_str = json_str[:500] + "..."
                    print(f"   📄 Sample JSON:")
                    print("      " + json_str.replace('\n', '\n      '))
                    
                except json.JSONDecodeError as e:
                    print(f"   ❌ Error parsing response_json: {e}")
                    print(f"   Raw JSON: {response.response_json[:200]}...")
            else:
                print(f"   ⚠️  No response_json data")
            
            # Check response_text for score mentions
            if response.response_text:
                text_lower = response.response_text.lower()
                score_mentions = []
                for score_word in ['score', 'rating', 'confidence', 'probability']:
                    if score_word in text_lower:
                        score_mentions.append(score_word)
                
                if score_mentions:
                    print(f"   📝 Score mentions in text: {score_mentions}")
                    # Show lines containing score words
                    lines = response.response_text.split('\n')
                    score_lines = [line.strip() for line in lines if any(word in line.lower() for word in score_mentions)]
                    if score_lines:
                        print(f"   📄 Score-related lines:")
                        for line in score_lines[:3]:  # Show first 3 lines
                            print(f"      {line}")
                else:
                    print(f"   ⚠️  No score mentions in response text")
            else:
                print(f"   ⚠️  No response_text data")
            
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking responses: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        session.close()

def check_database_schema():
    """Check if there are any score-related fields in the database schema"""
    print("🗄️  Checking Database Schema for Score Fields")
    print("=" * 50)
    
    # Check LlmResponse table structure
    from sqlalchemy import inspect
    from database import engine
    
    inspector = inspect(engine)
    
    # Get column info for llm_responses table
    columns = inspector.get_columns('llm_responses')
    
    print("📋 LlmResponse table columns:")
    score_columns = []
    for column in columns:
        column_name = column['name']
        column_type = str(column['type'])
        print(f"   {column_name}: {column_type}")
        
        if any(score_word in column_name.lower() for score_word in ['score', 'rating', 'confidence', 'probability']):
            score_columns.append(column_name)
    
    if score_columns:
        print(f"🎯 Score-related columns found: {score_columns}")
    else:
        print("⚠️  No dedicated score columns found in schema")
    
    print()

if __name__ == "__main__":
    print("🔍 Analysis Status Response Checker")
    print("=" * 60)
    print()
    
    # Check database schema first
    check_database_schema()
    
    # Check recent response data
    success = check_recent_responses()
    
    print("=" * 60)
    if success:
        print("✅ Analysis completed - check output above for score data")
    else:
        print("❌ Analysis failed or no data found")
