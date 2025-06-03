#!/usr/bin/env python3
"""
Test RAG API call for llm_responses ID 167
"""

import json
import requests
from utils.llm_config_formatter import format_llm_config_for_rag_api

# Connection details from the database
connection_details = {
    "id": 1,
    "name": "My Local Ollama Connection",
    "api_key": None,
    "port_no": None,
    "base_url": "http://studio.local:11434",
    "model_id": 8,
    "provider_id": 1,
    "connection_config": {}
}

# Document ID from docs table
document_id = "batch_79_doc_6534"

# Sample prompt (we'll use prompt ID 1)
prompt_text = "Analyze this document and provide insights."

# Format the config for RAG API
formatted_config = format_llm_config_for_rag_api(connection_details)
print("Formatted LLM Config:")
print(json.dumps(formatted_config, indent=2))

# Prepare form data
form_data = {
    'doc_id': document_id,
    'prompts': json.dumps([{"prompt": prompt_text}]),
    'llm_provider': json.dumps(formatted_config),
    'meta_data': json.dumps({})
}

print("\nForm data being sent:")
for key, value in form_data.items():
    print(f"{key}: {value[:100]}..." if len(value) > 100 else f"{key}: {value}")

# Make the request
rag_api_url = "http://localhost:7001"
print(f"\nCalling {rag_api_url}/analyze_document_with_llm...")

try:
    response = requests.post(
        f"{rag_api_url}/analyze_document_with_llm",
        data=form_data,
        timeout=60
    )
    
    print(f"\nResponse status code: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nResponse JSON:")
        print(json.dumps(result, indent=2))
    else:
        print(f"\nResponse text: {response.text}")
        
except Exception as e:
    print(f"\nError: {e}")