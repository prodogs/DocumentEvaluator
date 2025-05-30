#!/usr/bin/env python3
"""
Script to add sample data to the Document Batch Processor database
"""

from database import SessionLocal
from models import LlmConfiguration, Prompt, Folder

def add_sample_data():
    """Add sample LLM configurations, prompts, and folders"""
    print("Creating database session...")
    session = SessionLocal()
    
    try:
        # Check if data already exists
        existing_configs = session.query(LlmConfiguration).count()
        existing_prompts = session.query(Prompt).count()
        existing_folders = session.query(Folder).count()
        
        print(f"Current data: {existing_configs} configs, {existing_prompts} prompts, {existing_folders} folders")
        
        # Add sample LLM Configuration if none exist
        if existing_configs == 0:
            print("Adding sample LLM Configuration...")
            llm_config = LlmConfiguration(
                llm_name='OpenAI GPT-4',
                base_url='https://api.openai.com/v1',
                model_name='gpt-4',
                api_key='your-api-key-here',
                provider_type='openai',
                port_no=443,
                active=1
            )
            session.add(llm_config)
            
            # Add another LLM config for variety
            llm_config2 = LlmConfiguration(
                llm_name='Local LLM Service',
                base_url='http://localhost:7001',
                model_name='local-model',
                api_key='',
                provider_type='local',
                port_no=7001,
                active=1
            )
            session.add(llm_config2)
        
        # Add sample Prompts if none exist
        if existing_prompts == 0:
            print("Adding sample Prompts...")
            prompt1 = Prompt(
                prompt_text='Analyze this document and provide a comprehensive evaluation of its content, structure, and quality.',
                description='Document Quality Analysis',
                active=1
            )
            session.add(prompt1)
            
            prompt2 = Prompt(
                prompt_text='Summarize the key points and main themes of this document.',
                description='Document Summary',
                active=1
            )
            session.add(prompt2)
        
        # Add sample Folders if none exist
        if existing_folders == 0:
            print("Adding sample Folders...")
            folder1 = Folder(
                folder_path='/Users/frankfilippis/Documents/SampleDocs',
                folder_name='Sample Documents',
                active=1,
                status='NOT_PROCESSED'
            )
            session.add(folder1)
            
            folder2 = Folder(
                folder_path='/Users/frankfilippis/Desktop/TestDocs',
                folder_name='Test Documents',
                active=1,
                status='NOT_PROCESSED'
            )
            session.add(folder2)
        
        # Commit all changes
        print("Committing changes...")
        session.commit()
        
        # Verify the data was added
        final_configs = session.query(LlmConfiguration).count()
        final_prompts = session.query(Prompt).count()
        final_folders = session.query(Folder).count()
        
        print("✅ Sample data added successfully!")
        print(f"Final counts: {final_configs} configs, {final_prompts} prompts, {final_folders} folders")
        
        # List the added items
        print("\nAdded LLM Configurations:")
        for config in session.query(LlmConfiguration).all():
            print(f"  - {config.llm_name} ({config.provider_type})")
            
        print("\nAdded Prompts:")
        for prompt in session.query(Prompt).all():
            print(f"  - {prompt.description}")
            
        print("\nAdded Folders:")
        for folder in session.query(Folder).all():
            print(f"  - {folder.folder_name} ({folder.folder_path})")
        
    except Exception as e:
        print(f"❌ Error adding sample data: {e}")
        session.rollback()
        raise
    finally:
        session.close()
        print("Database session closed.")

if __name__ == "__main__":
    add_sample_data()
