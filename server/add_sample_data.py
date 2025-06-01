#!/usr/bin/env python3
"""
Script to add sample data to the Document Batch Processor database
"""

from database import SessionLocal
from models import Prompt, Folder, Connection, LlmProvider

def add_sample_data():
    """Add sample LLM configurations, prompts, and folders"""
    print("Creating database session...")
    session = SessionLocal()
    
    try:
        # Check if data already exists
        existing_configs = session.query(Connection).count()
        existing_prompts = session.query(Prompt).count()
        existing_folders = session.query(Folder).count()

        print(f"Current data: {existing_configs} connections, {existing_prompts} prompts, {existing_folders} folders")

        # Add sample Connection if none exist (replaces deprecated LlmConfiguration)
        if existing_configs == 0:
            print("Adding sample Connection...")
            # First ensure we have a provider
            provider = session.query(LlmProvider).filter_by(name='OpenAI').first()
            if not provider:
                provider = LlmProvider(
                    name='OpenAI',
                    provider_type='openai',
                    default_base_url='https://api.openai.com/v1',
                    supports_model_discovery=True,
                    auth_type='api_key'
                )
                session.add(provider)
                session.flush()  # Get the ID

            connection = Connection(
                name='OpenAI GPT-4',
                description='OpenAI GPT-4 connection',
                provider_id=provider.id,
                base_url='https://api.openai.com/v1',
                api_key='your-api-key-here',
                port_no=443,
                is_active=True
            )
            session.add(connection)
        
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
        final_configs = session.query(Connection).count()
        final_prompts = session.query(Prompt).count()
        final_folders = session.query(Folder).count()

        print("✅ Sample data added successfully!")
        print(f"Final counts: {final_configs} connections, {final_prompts} prompts, {final_folders} folders")

        # List the added items
        print("\nAdded Connections:")
        for config in session.query(Connection).all():
            print(f"  - {config.name} ({config.base_url})")
            
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
