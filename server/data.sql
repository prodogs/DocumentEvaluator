-- Sample data for the folders table
INSERT INTO folders (folder_path, folder_name) VALUES ('/Users/frankfilippis/GitHub/DocumentEvaluator/doc', 'Sample Documents');

-- Sample data for LLM Configurations
INSERT INTO llm_configurations (llm_name, base_url, model_name, api_key, provider_type, port_no) VALUES ('Mistral-7B-Instruct-v0.2', 'http://localhost:8000', 'mistral-7b-instruct-v0.2', 'YOUR_API_KEY_HERE', 'ollama', 8000);

-- Sample data for Prompts
INSERT INTO prompts (prompt_text, description) VALUES ('Summarize the following document:', 'A general summarization prompt.');