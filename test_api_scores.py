#!/usr/bin/env python3
"""
Test the API endpoints to verify score data is returned correctly
"""

import requests
import json

def test_batch_api():
    """Test the batch API to see if scores are included"""
    print("🌐 Testing Batch API for Score Data")
    print("=" * 50)

    try:
        # Get batches
        response = requests.get("http://localhost:5001/api/batches", timeout=10)
        print(f"📊 Batches API Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            # Handle different response formats
            if isinstance(data, list):
                batches = data
            elif isinstance(data, dict) and 'batches' in data:
                batches = data['batches']
            else:
                batches = [data] if data else []

            print(f"✅ Found {len(batches)} batches")

            if batches:
                # Test the first batch
                batch = batches[0]
                batch_id = batch['id']
                print(f"🔍 Testing batch ID: {batch_id} ({batch['batch_name']})")

                # Get LLM responses for this batch
                responses_url = f"http://localhost:5001/api/batches/{batch_id}/llm-responses"
                responses_response = requests.get(responses_url, timeout=10)
                print(f"📊 LLM Responses API Status: {responses_response.status_code}")

                if responses_response.status_code == 200:
                    data = responses_response.json()
                    responses = data.get('responses', [])  # Updated field name
                    print(f"✅ Found {len(responses)} LLM responses")

                    # Check for scores
                    scored_responses = [r for r in responses if r.get('overall_score') is not None]
                    print(f"🎯 Responses with scores: {len(scored_responses)}")

                    if scored_responses:
                        print(f"\n📋 Score Details:")
                        for response in scored_responses[:3]:  # Show first 3
                            score = response.get('overall_score')
                            document_name = response.get('document', {}).get('filename', 'Unknown')
                            status = response.get('status')
                            print(f"   ID {response['id']}: {score}/100 - {document_name} ({status})")

                            # Check if response_json contains scoring data
                            response_json = response.get('response_json')
                            if response_json:
                                try:
                                    if isinstance(response_json, str):
                                        json_data = json.loads(response_json)
                                    else:
                                        json_data = response_json

                                    scoring_result = json_data.get('scoring_result', {})
                                    if scoring_result:
                                        confidence = scoring_result.get('confidence')
                                        subscores = scoring_result.get('subscores', {})
                                        print(f"      Confidence: {confidence}")
                                        print(f"      Subscores: {len(subscores)} categories")
                                    else:
                                        print(f"      ⚠️  No scoring_result in JSON")
                                except Exception as e:
                                    print(f"      ❌ Error parsing JSON: {e}")

                        return True
                    else:
                        print(f"⚠️  No responses with scores found")
                        return False
                else:
                    print(f"❌ Error getting LLM responses: {responses_response.text}")
                    return False
            else:
                print(f"⚠️  No batches found")
                return False
        else:
            print(f"❌ Error getting batches: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_direct_response_api():
    """Test the LLM responses list API to find our test data"""
    print(f"\n🌐 Testing LLM Responses List API")
    print("=" * 50)

    try:
        # Get LLM responses list
        url = "http://localhost:5001/api/llm-responses?limit=10"

        response = requests.get(url, timeout=10)
        print(f"📊 LLM Responses List API Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            responses = data.get('responses', [])
            print(f"✅ Found {len(responses)} LLM responses")

            # Look for responses with scores
            scored_responses = [r for r in responses if r.get('overall_score') is not None]
            print(f"🎯 Responses with scores: {len(scored_responses)}")

            if scored_responses:
                print(f"\n📋 Score Details from List API:")
                for response in scored_responses[:3]:  # Show first 3
                    score = response.get('overall_score')
                    response_id = response.get('id')
                    task_id = response.get('task_id', 'N/A')
                    print(f"   ID {response_id}: {score}/100 (Task: {task_id})")

                    # Check if response_json contains scoring data
                    response_json = response.get('response_json')
                    if response_json:
                        try:
                            if isinstance(response_json, str):
                                json_data = json.loads(response_json)
                            else:
                                json_data = response_json

                            scoring_result = json_data.get('scoring_result', {})
                            if scoring_result:
                                confidence = scoring_result.get('confidence')
                                subscores = scoring_result.get('subscores', {})
                                print(f"      Confidence: {confidence}")
                                print(f"      Subscores: {len(subscores)} categories")
                            else:
                                print(f"      ⚠️  No scoring_result in JSON")
                        except Exception as e:
                            print(f"      ❌ Error parsing JSON: {e}")

                return True
            else:
                print(f"⚠️  No responses with scores found")
                return False
        else:
            print(f"❌ Error getting responses: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 API Score Data Test")
    print("=" * 60)

    # Test batch API
    batch_success = test_batch_api()

    # Test direct response API
    response_success = test_direct_response_api()

    print("\n" + "=" * 60)
    if batch_success and response_success:
        print("✅ All API tests passed!")
        print("🎉 Score data is being returned correctly by the APIs")
        print("🌐 The UI should now display scores and detailed views")
    else:
        print("❌ Some API tests failed")
        print(f"   Batch API: {'✅' if batch_success else '❌'}")
        print(f"   Response API: {'✅' if response_success else '❌'}")
