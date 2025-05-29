-- Schema for the folders table
CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT NOT NULL UNIQUE,
    folder_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Schema for LLM Configurations
CREATE TABLE IF NOT EXISTS llm_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    llm_name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    model_name TEXT NOT NULL,
    api_key TEXT,
    provider_type TEXT NOT NULL,
    port_no INTEGER
);

-- Schema for Prompts
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_text TEXT NOT NULL,
    description TEXT
);

-- Schema for Documents
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL UNIQUE,
    folder_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (folder_id) REFERENCES folders(id)
);

-- Schema for LLM Responses
CREATE TABLE IF NOT EXISTS llm_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    prompt_id INTEGER NOT NULL,
    llm_name TEXT NOT NULL,
    task_id TEXT,
    status TEXT NOT NULL, -- 'P' for pending, 'R' for running, 'S' for success, 'F' for failed
    started_processing_at TIMESTAMP,
    completed_processing_at TIMESTAMP,
    response_json TEXT,
    response_text TEXT, -- Added missing column
    response_time_ms INTEGER,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id),
    FOREIGN KEY (prompt_id) REFERENCES prompts(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_folder_path ON folders(folder_path);
CREATE INDEX IF NOT EXISTS idx_document_filepath ON documents(filepath);
CREATE INDEX IF NOT EXISTS idx_llm_response_document_id ON llm_responses(document_id);
CREATE INDEX IF NOT EXISTS idx_llm_response_prompt_id ON llm_responses(prompt_id);
CREATE INDEX IF NOT EXISTS idx_llm_response_task_id ON llm_responses(task_id);
