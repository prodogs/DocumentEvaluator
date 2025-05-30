#!/usr/bin/env python3
"""
Script to submit a fresh document analysis and check the response format
to see if scores are included in the analysis_status response.
"""

import sys
import os
import json
import requests
import time
from datetime import datetime

def submit_test_document():
    """Submit a test document for analysis"""
    print("📤 Submitting Test Document for Analysis")
    print("=" * 50)

    # Create test content
    test_content = """
    This is a test document for score verification.

    The document contains information about a product evaluation.
    Quality: Excellent
    Performance: High
    Reliability: Good

    Overall assessment: This product meets all requirements.
    """

    # Prepare the request
    url = "http://localhost:7001/analyze_document_with_llm"

    # Test prompts that might generate scores
    prompts = [
        {
            "prompt": "Evaluate this document for LLM readiness. Rate its suitability on a scale of 0-100 and provide detailed scoring with confidence levels."
        }
    ]

    # Test LLM provider configuration
    llm_provider = {
        "provider_type": "ollama",
        "url": "http://localhost:11434",
        "model_name": "llama3.2:latest"
    }

    # Prepare multipart form data
    files = {
        'file': ('test_score_document.txt', test_content.encode('utf-8'), 'text/plain')
    }

    data = {
        'filename': 'test_score_document.txt',
        'prompts': json.dumps(prompts),
        'llm_provider': json.dumps(llm_provider)
    }

    print(f"🌐 Submitting to: {url}")
    print(f"📋 Prompt: {prompts[0]['prompt']}")
    print(f"🤖 LLM: {llm_provider['model_name']}")

    try:
        response = requests.post(url, files=files, data=data, timeout=30)
        print(f"📊 Response Status: {response.status_code}")

        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ Document submitted successfully")
                print(f"📄 Response: {json.dumps(result, indent=2)}")

                task_id = result.get('task_id')
                if task_id:
                    print(f"🎯 Task ID: {task_id}")
                    return task_id
                else:
                    print(f"❌ No task_id in response")
                    return None

            except json.JSONDecodeError as e:
                print(f"❌ Error parsing JSON: {e}")
                print(f"Raw response: {response.text}")
                return None
        else:
            print(f"❌ Submission failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def monitor_task_status(task_id, max_wait_time=120):
    """Monitor task status until completion"""
    print(f"\n🔍 Monitoring Task Status: {task_id}")
    print("=" * 50)

    start_time = time.time()
    check_count = 0

    while time.time() - start_time < max_wait_time:
        check_count += 1
        url = f"http://localhost:7001/analyze_status/{task_id}"

        try:
            response = requests.get(url, timeout=10)
            print(f"📊 Check {check_count}: Status {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    status = data.get('status', 'UNKNOWN')
                    print(f"   Task Status: {status}")

                    if status.upper() in ['COMPLETED', 'SUCCESS', 'FAILED', 'ERROR']:
                        print(f"✅ Task completed with status: {status}")
                        print(f"📄 Final Response:")
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

                        # Check results structure
                        if 'results' in data:
                            results = data['results']
                            print(f"\n📋 Results Analysis:")
                            if isinstance(results, list):
                                for i, result in enumerate(results):
                                    print(f"\n   Result {i+1}:")
                                    if isinstance(result, dict):
                                        for key, value in result.items():
                                            if any(score_word in key.lower() for score_word in ['score', 'rating', 'confidence', 'probability']):
                                                print(f"      🎯 {key}: {value}")
                                            else:
                                                value_str = str(value)
                                                if len(value_str) > 200:
                                                    value_str = value_str[:200] + "..."
                                                print(f"      {key}: {value_str}")

                        return data

                    elif status.upper() in ['PROCESSING', 'PENDING', 'STARTED']:
                        print(f"   ⏳ Still processing...")
                    else:
                        print(f"   ❓ Unknown status: {status}")

                except json.JSONDecodeError as e:
                    print(f"   ❌ Error parsing JSON: {e}")
                    print(f"   Raw response: {response.text[:200]}...")

            elif response.status_code == 404:
                print(f"   ❌ Task not found (404)")
                return None
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text[:100]}...")

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")

        # Wait before next check
        time.sleep(5)

    print(f"⏰ Timeout reached after {max_wait_time} seconds")
    return None

if __name__ == "__main__":
    print("🔍 Fresh Analysis Status Response Checker")
    print("=" * 60)

    # Submit a test document
    task_id = submit_test_document()

    if task_id:
        # Monitor the task until completion
        final_result = monitor_task_status(task_id)

        print("\n" + "=" * 60)
        if final_result:
            print("✅ Successfully captured analysis response")
            print("🔍 Check the output above to see if scores are included")
        else:
            print("❌ Failed to get final analysis response")
    else:
        print("❌ Failed to submit test document")
