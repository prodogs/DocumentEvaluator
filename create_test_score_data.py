#!/usr/bin/env python3
"""
Create test data with scores to verify the UI implementation
"""

import sys
import os
import json
from datetime import datetime

# Add the server directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import LlmResponse, Document, Prompt, LlmConfiguration, Batch
from sqlalchemy.sql import func

def create_test_score_data():
    """Create test LLM responses with score data"""
    print("🧪 Creating Test Score Data")
    print("=" * 50)

    session = Session()

    try:
        # Get existing records to use as foreign keys
        document = session.query(Document).first()
        prompt = session.query(Prompt).first()
        llm_config = session.query(LlmConfiguration).first()
        batch = session.query(Batch).first()

        if not all([document, prompt, llm_config, batch]):
            print("❌ Missing required records. Need at least one document, prompt, llm_config, and batch")
            print(f"   Documents: {session.query(Document).count()}")
            print(f"   Prompts: {session.query(Prompt).count()}")
            print(f"   LLM Configs: {session.query(LlmConfiguration).count()}")
            print(f"   Batches: {session.query(Batch).count()}")
            return False

        print(f"✅ Found required records:")
        print(f"   Document: {document.filename}")
        print(f"   Prompt: {prompt.description}")
        print(f"   LLM Config: {llm_config.llm_name}")
        print(f"   Batch: {batch.batch_name}")

        # Create test responses with different scores
        test_responses = [
            {
                "overall_score": 95.0,
                "status": "S",
                "response_text": "=== SCORING RESULTS ===\nOverall Suitability Score: 95/100\nConfidence: 92\nProvider: test_provider\n\nSubscores:\n  Content Quality: 98 - Excellent structure and clarity\n  Technical Accuracy: 94 - Minor technical gaps\n  Practical Utility: 96 - Highly actionable\n\nImprovement Recommendations:\n  1. Add more examples\n  2. Include troubleshooting section\n\n" + "="*50 + "\n\n=== PROMPT RESULTS ===\nPrompt 1: Test prompt for excellent document\nStatus: success\nResponse: This document demonstrates excellent quality with clear structure, comprehensive content, and high practical value.",
                "response_json": {
                    "task_id": "test-task-excellent",
                    "status": "success",
                    "results": [
                        {
                            "prompt": "Test prompt for excellent document",
                            "response": "This document demonstrates excellent quality with clear structure, comprehensive content, and high practical value.",
                            "status": "success",
                            "error_message": None
                        }
                    ],
                    "scoring_result": {
                        "overall_score": 95,
                        "subscores": {
                            "Content Quality": {"score": 98, "comment": "Excellent structure and clarity"},
                            "Technical Accuracy": {"score": 94, "comment": "Minor technical gaps"},
                            "Practical Utility": {"score": 96, "comment": "Highly actionable"}
                        },
                        "improvement_recommendations": ["Add more examples", "Include troubleshooting section"],
                        "confidence": 92,
                        "provider_name": "test_provider",
                        "timestamp": "2025-05-30T01:00:00.000000"
                    }
                }
            },
            {
                "overall_score": 72.0,
                "status": "S",
                "response_text": "=== SCORING RESULTS ===\nOverall Suitability Score: 72/100\nConfidence: 78\nProvider: test_provider\n\nSubscores:\n  Content Quality: 75 - Good organization\n  Technical Accuracy: 68 - Some inconsistencies\n  Practical Utility: 74 - Moderately useful\n\nImprovement Recommendations:\n  1. Improve technical accuracy\n  2. Add more detailed examples\n\n" + "="*50 + "\n\n=== PROMPT RESULTS ===\nPrompt 1: Test prompt for good document\nStatus: success\nResponse: This document shows good quality with room for improvement in technical accuracy and detail.",
                "response_json": {
                    "task_id": "test-task-good",
                    "status": "success",
                    "results": [
                        {
                            "prompt": "Test prompt for good document",
                            "response": "This document shows good quality with room for improvement in technical accuracy and detail.",
                            "status": "success",
                            "error_message": None
                        }
                    ],
                    "scoring_result": {
                        "overall_score": 72,
                        "subscores": {
                            "Content Quality": {"score": 75, "comment": "Good organization"},
                            "Technical Accuracy": {"score": 68, "comment": "Some inconsistencies"},
                            "Practical Utility": {"score": 74, "comment": "Moderately useful"}
                        },
                        "improvement_recommendations": ["Improve technical accuracy", "Add more detailed examples"],
                        "confidence": 78,
                        "provider_name": "test_provider",
                        "timestamp": "2025-05-30T01:05:00.000000"
                    }
                }
            },
            {
                "overall_score": 45.0,
                "status": "S",
                "response_text": "=== SCORING RESULTS ===\nOverall Suitability Score: 45/100\nConfidence: 65\nProvider: test_provider\n\nSubscores:\n  Content Quality: 50 - Basic structure\n  Technical Accuracy: 38 - Multiple errors\n  Practical Utility: 47 - Limited usefulness\n\nImprovement Recommendations:\n  1. Fix technical errors\n  2. Improve content structure\n  3. Add practical examples\n\n" + "="*50 + "\n\n=== PROMPT RESULTS ===\nPrompt 1: Test prompt for poor document\nStatus: success\nResponse: This document has significant issues that need to be addressed before it can be effectively used.",
                "response_json": {
                    "task_id": "test-task-poor",
                    "status": "success",
                    "results": [
                        {
                            "prompt": "Test prompt for poor document",
                            "response": "This document has significant issues that need to be addressed before it can be effectively used.",
                            "status": "success",
                            "error_message": None
                        }
                    ],
                    "scoring_result": {
                        "overall_score": 45,
                        "subscores": {
                            "Content Quality": {"score": 50, "comment": "Basic structure"},
                            "Technical Accuracy": {"score": 38, "comment": "Multiple errors"},
                            "Practical Utility": {"score": 47, "comment": "Limited usefulness"}
                        },
                        "improvement_recommendations": ["Fix technical errors", "Improve content structure", "Add practical examples"],
                        "confidence": 65,
                        "provider_name": "test_provider",
                        "timestamp": "2025-05-30T01:10:00.000000"
                    }
                }
            }
        ]

        created_responses = []

        for i, test_data in enumerate(test_responses, 1):
            print(f"\n📝 Creating test response {i} (Score: {test_data['overall_score']})")

            response = LlmResponse(
                document_id=document.id,
                prompt_id=prompt.id,
                llm_config_id=llm_config.id,
                llm_name=llm_config.llm_name,
                task_id=test_data['response_json']['task_id'],
                status=test_data['status'],
                started_processing_at=func.now(),
                completed_processing_at=func.now(),
                response_text=test_data['response_text'],
                response_json=json.dumps(test_data['response_json']),
                response_time_ms=1500 + (i * 200),  # Varying response times
                overall_score=test_data['overall_score'],
                error_message=None
            )

            session.add(response)
            session.flush()  # Get the ID
            created_responses.append(response)

            print(f"   ✅ Created response ID: {response.id}")

        session.commit()

        print(f"\n🎉 Successfully created {len(created_responses)} test responses with scores!")
        print(f"\nScore Summary:")
        for response in created_responses:
            score_class = "Excellent" if response.overall_score >= 80 else "Good" if response.overall_score >= 60 else "Fair" if response.overall_score >= 40 else "Poor"
            print(f"   ID {response.id}: {response.overall_score}/100 ({score_class})")

        return True

    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False

    finally:
        session.close()

def verify_test_data():
    """Verify the test data was created correctly"""
    print(f"\n🔍 Verifying Test Data")
    print("=" * 50)

    session = Session()
    try:
        # Get responses with scores
        scored_responses = session.query(LlmResponse).filter(
            LlmResponse.overall_score.isnot(None)
        ).order_by(LlmResponse.overall_score.desc()).all()

        print(f"📊 Found {len(scored_responses)} responses with scores:")

        for response in scored_responses:
            print(f"\n📋 Response ID: {response.id}")
            print(f"   Score: {response.overall_score}/100")
            print(f"   Status: {response.status}")
            print(f"   Task ID: {response.task_id}")
            print(f"   Document: {response.document.filename if response.document else 'N/A'}")
            print(f"   LLM Config: {response.llm_config.llm_name if response.llm_config else 'N/A'}")

            # Check JSON structure
            if response.response_json:
                try:
                    data = json.loads(response.response_json)
                    scoring_result = data.get('scoring_result', {})
                    if scoring_result:
                        print(f"   JSON Score: {scoring_result.get('overall_score')}")
                        print(f"   Confidence: {scoring_result.get('confidence')}")
                        subscores = scoring_result.get('subscores', {})
                        print(f"   Subscores: {len(subscores)} categories")
                except:
                    print(f"   ⚠️  Error parsing JSON")

        return len(scored_responses) > 0

    except Exception as e:
        print(f"❌ Error verifying data: {e}")
        return False

    finally:
        session.close()

if __name__ == "__main__":
    print("🧪 Test Score Data Creator")
    print("=" * 60)

    success = create_test_score_data()

    if success:
        verify_test_data()
        print("\n" + "=" * 60)
        print("✅ Test data creation completed!")
        print("🌐 You can now test the UI by viewing the Batch Management page")
        print("   The responses should show suitability scores and be clickable for details")
    else:
        print("\n" + "=" * 60)
        print("❌ Test data creation failed!")
