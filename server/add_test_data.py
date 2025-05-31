#!/usr/bin/env python3
"""
Add test data for connection manager testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Session
from minimal_server import LlmProvider, Model, ModelProvider

def add_test_data():
    session = Session()
    
    try:
        # Add providers
        providers = [
            LlmProvider(
                name="LM Studio (lmstudio)",
                provider_type="local",
                default_base_url="http://localhost:1234",
                auth_type="none",
                notes="Local LM Studio instance"
            ),
            LlmProvider(
                name="OpenAI",
                provider_type="cloud",
                default_base_url="https://api.openai.com/v1",
                auth_type="api_key",
                notes="OpenAI cloud service"
            ),
            LlmProvider(
                name="Anthropic",
                provider_type="cloud",
                default_base_url="https://api.anthropic.com",
                auth_type="api_key",
                notes="Anthropic Claude API"
            )
        ]
        
        for provider in providers:
            existing = session.query(LlmProvider).filter_by(name=provider.name).first()
            if not existing:
                session.add(provider)
        
        session.commit()
        
        # Add models
        models = [
            Model(
                display_name="Qwen 2.5 8B",
                common_name="qwen/qwen3-8b",
                model_family="Qwen",
                context_length=32768,
                parameter_count="8B",
                notes="Good general purpose model"
            ),
            Model(
                display_name="GPT-4",
                common_name="gpt-4",
                model_family="GPT",
                context_length=8192,
                parameter_count="Unknown",
                notes="Advanced reasoning capabilities"
            ),
            Model(
                display_name="Claude 3.5 Sonnet",
                common_name="claude-3-5-sonnet-20241022",
                model_family="Claude",
                context_length=200000,
                parameter_count="Unknown",
                notes="Excellent for analysis and reasoning"
            )
        ]
        
        for model in models:
            existing = session.query(Model).filter_by(common_name=model.common_name).first()
            if not existing:
                session.add(model)
        
        session.commit()
        
        # Add model-provider relationships
        # Get the actual objects from DB
        lm_studio = session.query(LlmProvider).filter_by(name="LM Studio (lmstudio)").first()
        openai = session.query(LlmProvider).filter_by(name="OpenAI").first()
        anthropic = session.query(LlmProvider).filter_by(name="Anthropic").first()
        
        qwen = session.query(Model).filter_by(common_name="qwen/qwen3-8b").first()
        gpt4 = session.query(Model).filter_by(common_name="gpt-4").first()
        claude = session.query(Model).filter_by(common_name="claude-3-5-sonnet-20241022").first()
        
        relationships = []
        if qwen and lm_studio:
            relationships.append(ModelProvider(model_id=qwen.id, provider_id=lm_studio.id))
        if gpt4 and openai:
            relationships.append(ModelProvider(model_id=gpt4.id, provider_id=openai.id))
        if claude and anthropic:
            relationships.append(ModelProvider(model_id=claude.id, provider_id=anthropic.id))
        
        for rel in relationships:
            existing = session.query(ModelProvider).filter_by(
                model_id=rel.model_id, 
                provider_id=rel.provider_id
            ).first()
            if not existing:
                session.add(rel)
        
        session.commit()
        
        print("✅ Test data added successfully!")
        print(f"   Providers: {len(providers)}")
        print(f"   Models: {len(models)}")
        print(f"   Relationships: {len(relationships)}")
        
    except Exception as e:
        print(f"❌ Error adding test data: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    add_test_data()
