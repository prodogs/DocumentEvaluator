#!/usr/bin/env python3
"""
Check Document-LLM-Prompt Combinations

Verify that all combinations are being created correctly
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session
from server.models import Document, LlmResponse, LlmConfiguration, Prompt
from sqlalchemy import func

def check_combinations():
    """Check if all document-LLM-prompt combinations are being created"""
    
    print("🔍 Document-LLM-Prompt Combinations Analysis")
    print("=" * 60)
    
    session = Session()
    
    try:
        # Get counts
        total_docs = session.query(Document).count()
        total_llm_configs = session.query(LlmConfiguration).filter(LlmConfiguration.active == 1).count()
        total_prompts = session.query(Prompt).filter(Prompt.active == 1).count()
        total_responses = session.query(LlmResponse).count()
        
        expected_combinations = total_docs * total_llm_configs * total_prompts
        
        print(f"📊 Current Counts:")
        print(f"   Documents: {total_docs}")
        print(f"   Active LLM Configs: {total_llm_configs}")
        print(f"   Active Prompts: {total_prompts}")
        print(f"   LLM Responses: {total_responses}")
        print(f"   Expected Combinations: {expected_combinations}")
        print()
        
        if total_responses == expected_combinations:
            print("✅ All combinations are present!")
        else:
            print(f"⚠️  Missing combinations: {expected_combinations - total_responses}")
        
        # Show active LLM configs
        print("🤖 Active LLM Configurations:")
        print("-" * 35)
        llm_configs = session.query(LlmConfiguration).filter(LlmConfiguration.active == 1).all()
        for config in llm_configs:
            print(f"   {config.id}: {config.llm_name} ({config.model_name})")
        
        # Show active prompts
        print("\n📝 Active Prompts:")
        print("-" * 20)
        prompts = session.query(Prompt).filter(Prompt.active == 1).all()
        for prompt in prompts:
            print(f"   {prompt.id}: {prompt.prompt_text[:50]}...")
        
        # Show combination matrix
        print(f"\n📋 Combination Matrix:")
        print("-" * 25)
        
        # Get documents with their response counts
        doc_response_counts = session.query(
            Document.id,
            Document.filename,
            func.count(LlmResponse.id).label('response_count')
        ).outerjoin(LlmResponse, Document.id == LlmResponse.document_id)\
         .group_by(Document.id, Document.filename)\
         .order_by(Document.id).all()
        
        for doc_id, filename, response_count in doc_response_counts:
            expected_for_doc = total_llm_configs * total_prompts
            status = "✅" if response_count == expected_for_doc else "⚠️"
            print(f"   Doc {doc_id}: {response_count}/{expected_for_doc} responses {status}")
            print(f"      File: {filename}")
            
            # Show detailed breakdown for this document
            if response_count != expected_for_doc:
                print(f"      Missing combinations for this document!")
                
                # Show which combinations exist
                existing_combinations = session.query(
                    LlmResponse.llm_config_id,
                    LlmResponse.prompt_id
                ).filter(LlmResponse.document_id == doc_id).all()
                
                print(f"      Existing: {len(existing_combinations)} combinations")
                for llm_id, prompt_id in existing_combinations:
                    print(f"        LLM {llm_id} + Prompt {prompt_id}")
        
        # Show recent processing activity
        print(f"\n🔄 Recent LLM Response Activity:")
        print("-" * 35)
        
        recent_responses = session.query(LlmResponse).order_by(LlmResponse.timestamp.desc()).limit(5).all()
        
        for resp in recent_responses:
            doc = session.query(Document).filter(Document.id == resp.document_id).first()
            doc_name = doc.filename if doc else "Unknown"
            
            print(f"   Response ID: {resp.id}")
            print(f"     Document: {doc_name}")
            print(f"     LLM Config: {resp.llm_config_id}")
            print(f"     Prompt: {resp.prompt_id}")
            print(f"     Status: {resp.status}")
            print(f"     Timestamp: {resp.timestamp}")
            print()
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return False

def check_missing_combinations():
    """Check for missing combinations specifically"""
    
    print("\n🔍 Missing Combinations Analysis")
    print("=" * 40)
    
    session = Session()
    
    try:
        # Get all active configs and prompts
        llm_configs = session.query(LlmConfiguration).filter(LlmConfiguration.active == 1).all()
        prompts = session.query(Prompt).filter(Prompt.active == 1).all()
        documents = session.query(Document).all()
        
        print(f"Checking {len(documents)} docs × {len(llm_configs)} LLMs × {len(prompts)} prompts")
        
        missing_count = 0
        
        for doc in documents:
            for llm_config in llm_configs:
                for prompt in prompts:
                    # Check if this combination exists
                    existing = session.query(LlmResponse).filter(
                        LlmResponse.document_id == doc.id,
                        LlmResponse.llm_config_id == llm_config.id,
                        LlmResponse.prompt_id == prompt.id
                    ).first()
                    
                    if not existing:
                        missing_count += 1
                        print(f"❌ Missing: Doc {doc.id} + LLM {llm_config.id} + Prompt {prompt.id}")
                        print(f"   File: {doc.filename}")
                        print(f"   LLM: {llm_config.llm_name}")
                        print(f"   Prompt: {prompt.prompt_text[:30]}...")
                        print()
        
        if missing_count == 0:
            print("✅ No missing combinations found!")
        else:
            print(f"⚠️  Found {missing_count} missing combinations")
        
        session.close()
        return missing_count == 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return False

def main():
    """Main function"""
    
    print("🚀 Document Combinations Verification")
    print("=" * 50)
    print("Host: tablemini.local:5432")
    print("Database: doc_eval")
    print()
    
    # Check combinations
    combinations_ok = check_combinations()
    missing_ok = check_missing_combinations()
    
    print("\n" + "=" * 50)
    if combinations_ok and missing_ok:
        print("✅ All document-LLM-prompt combinations are correct!")
        print("💡 The system is working as designed:")
        print("   - Documents table: unique files")
        print("   - LLM responses table: all combinations")
    else:
        print("⚠️  Some combinations are missing.")
        print("💡 This could indicate:")
        print("   - Processing was interrupted")
        print("   - New LLM configs/prompts were added")
        print("   - Database transaction issues")

if __name__ == "__main__":
    main()
