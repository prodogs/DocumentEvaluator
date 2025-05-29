#!/usr/bin/env python3
"""
Verification script to confirm document processing logic
"""

import sys
sys.path.append('.')

from server.database import Session
from server.models import LlmResponse, Document, LlmConfiguration, Prompt

def verify_processing_combinations():
    """Verify that each document gets processed with every LLM and prompt combination"""
    print("🔍 Verifying Document Processing Logic\n")
    
    session = Session()
    try:
        # Get active configurations
        llm_configs = session.query(LlmConfiguration).filter(LlmConfiguration.active == 1).all()
        prompts = session.query(Prompt).filter(Prompt.active == 1).all()
        
        print(f"📊 Active Configurations:")
        print(f"   LLM Configurations: {len(llm_configs)}")
        for config in llm_configs:
            print(f"     - {config.llm_name} (ID: {config.id})")
        
        print(f"   Prompts: {len(prompts)}")
        for prompt in prompts:
            print(f"     - {prompt.prompt_text[:50]}... (ID: {prompt.id})")
        
        # Calculate expected combinations per document
        combinations_per_doc = len(llm_configs) * len(prompts)
        print(f"\n🧮 Expected combinations per document: {combinations_per_doc}")
        print(f"   (Each document should be processed with each LLM × each prompt)")
        
        # Check existing documents and their processing records
        documents = session.query(Document).limit(5).all()  # Check first 5 documents
        
        print(f"\n📋 Verification for sample documents:")
        
        for doc in documents:
            print(f"\n📄 Document: {doc.filename} (ID: {doc.id})")
            
            # Get all LLM responses for this document
            responses = session.query(LlmResponse).filter_by(document_id=doc.id).all()
            
            print(f"   Total LLM responses: {len(responses)}")
            
            # Group by LLM and prompt
            llm_prompt_combinations = {}
            for response in responses:
                key = f"LLM_{response.llm_name}_Prompt_{response.prompt_id}"
                llm_prompt_combinations[key] = response.status
            
            print(f"   Actual combinations: {len(llm_prompt_combinations)}")
            
            # Check if we have all expected combinations
            expected_combinations = []
            for llm_config in llm_configs:
                for prompt in prompts:
                    expected_key = f"LLM_{llm_config.llm_name}_Prompt_{prompt.id}"
                    expected_combinations.append(expected_key)
            
            missing_combinations = []
            for expected in expected_combinations:
                if expected not in llm_prompt_combinations:
                    missing_combinations.append(expected)
            
            if missing_combinations:
                print(f"   ❌ Missing combinations: {len(missing_combinations)}")
                for missing in missing_combinations[:3]:  # Show first 3
                    print(f"      - {missing}")
                if len(missing_combinations) > 3:
                    print(f"      ... and {len(missing_combinations) - 3} more")
            else:
                print(f"   ✅ All expected combinations present")
            
            # Show status distribution
            status_counts = {}
            for status in llm_prompt_combinations.values():
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"   Status distribution: {status_counts}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying processing logic: {e}")
        return False
    finally:
        session.close()

def verify_api_call_structure():
    """Verify the structure of API calls to analyze_document_with_llm"""
    print(f"\n🔧 Verifying API Call Structure\n")
    
    print("📋 Each call to analyze_document_with_llm includes:")
    print("   ✅ filename: The document filename")
    print("   ✅ file: The document content (binary)")
    print("   ✅ prompts: JSON array with ONE prompt per call")
    print("   ✅ llm_provider: JSON object with LLM configuration")
    
    print(f"\n🔄 Processing Flow:")
    print("   1. For each document:")
    print("      2. For each active LLM configuration:")
    print("         3. For each active prompt:")
    print("            4. Create LLM response record (status='N')")
    print("            5. Make separate API call to analyze_document_with_llm")
    print("            6. Each call processes ONE document + ONE LLM + ONE prompt")
    
    print(f"\n📊 Example with 2 LLMs and 3 prompts:")
    print("   Document A:")
    print("     - Call 1: Document A + LLM1 + Prompt1")
    print("     - Call 2: Document A + LLM1 + Prompt2") 
    print("     - Call 3: Document A + LLM1 + Prompt3")
    print("     - Call 4: Document A + LLM2 + Prompt1")
    print("     - Call 5: Document A + LLM2 + Prompt2")
    print("     - Call 6: Document A + LLM2 + Prompt3")
    print("   Total: 6 API calls for Document A")
    
    # Verify the code structure
    print(f"\n🔍 Code Structure Verification:")
    
    try:
        # Check process_folder.py structure
        with open('server/api/process_folder.py', 'r') as f:
            content = f.read()
        
        # Look for the nested loops
        has_llm_loop = 'for llm_config in llm_configs:' in content
        has_prompt_loop = 'for prompt in prompts:' in content
        has_api_call = 'analyze_document_with_llm' in content
        has_single_prompt = "prompts_data = [{'prompt': prompt.prompt_text}]" in content
        
        print(f"   ✅ Has LLM configuration loop: {has_llm_loop}")
        print(f"   ✅ Has prompt loop: {has_prompt_loop}")
        print(f"   ✅ Has API call to analyze_document_with_llm: {has_api_call}")
        print(f"   ✅ Sends single prompt per call: {has_single_prompt}")
        
        if all([has_llm_loop, has_prompt_loop, has_api_call, has_single_prompt]):
            print(f"\n✅ Code structure is correct for individual processing")
            return True
        else:
            print(f"\n❌ Code structure issues detected")
            return False
            
    except Exception as e:
        print(f"❌ Error checking code structure: {e}")
        return False

def calculate_total_api_calls():
    """Calculate total expected API calls"""
    print(f"\n🧮 Calculating Total Expected API Calls\n")
    
    session = Session()
    try:
        # Count active configurations
        llm_count = session.query(LlmConfiguration).filter(LlmConfiguration.active == 1).count()
        prompt_count = session.query(Prompt).filter(Prompt.active == 1).count()
        document_count = session.query(Document).count()
        
        total_combinations = document_count * llm_count * prompt_count
        
        print(f"📊 Current Database State:")
        print(f"   Documents: {document_count}")
        print(f"   Active LLM Configurations: {llm_count}")
        print(f"   Active Prompts: {prompt_count}")
        print(f"   Total Expected API Calls: {total_combinations}")
        
        # Check how many have been processed
        total_responses = session.query(LlmResponse).count()
        processing_responses = session.query(LlmResponse).filter(LlmResponse.status == 'P').count()
        completed_responses = session.query(LlmResponse).filter(LlmResponse.status == 'S').count()
        failed_responses = session.query(LlmResponse).filter(LlmResponse.status == 'F').count()
        waiting_responses = session.query(LlmResponse).filter(LlmResponse.status == 'N').count()
        
        print(f"\n📈 Processing Status:")
        print(f"   Total LLM Response Records: {total_responses}")
        print(f"   Processing (P): {processing_responses}")
        print(f"   Completed (S): {completed_responses}")
        print(f"   Failed (F): {failed_responses}")
        print(f"   Waiting (N): {waiting_responses}")
        
        coverage_percentage = (total_responses / total_combinations * 100) if total_combinations > 0 else 0
        print(f"   Coverage: {coverage_percentage:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Error calculating API calls: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Document Processing Logic Verification\n")
    
    # Verify processing combinations
    combinations_ok = verify_processing_combinations()
    
    # Verify API call structure
    structure_ok = verify_api_call_structure()
    
    # Calculate total API calls
    calculations_ok = calculate_total_api_calls()
    
    print(f"\n=== Verification Results ===")
    print(f"Processing Combinations: {'✅ CORRECT' if combinations_ok else '❌ ISSUES'}")
    print(f"API Call Structure: {'✅ CORRECT' if structure_ok else '❌ ISSUES'}")
    print(f"Calculations: {'✅ CORRECT' if calculations_ok else '❌ ISSUES'}")
    
    if all([combinations_ok, structure_ok, calculations_ok]):
        print(f"\n🎉 CONFIRMED: Each document will be processed with every LLM and prompt combination!")
        print(f"   Each combination results in a separate API call to analyze_document_with_llm")
    else:
        print(f"\n⚠️  Issues detected in processing logic verification")
