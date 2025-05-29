# Document Processor UI Application Plan

### **Project Overview**

The goal is to build a React-based web application that allows users to select a folder, process supported document types (PDF, TXT, DOCX, XLSX) within that folder using an external LLM analysis API, store processing details and results in a database, and provide real-time progress and error reporting.

### **Architecture Diagram**

```mermaid
graph TD
    A[User Interface - React App] --> B(Backend Server - Node.js/Python)
    B --> C(File System Access)
    B --> D(Database - SQLite: llm_evaluation.db)
    B --> E(LLM Analysis API)

    subgraph UI Components
        A1[Folder Selection Component]
        A2[Progress Display Component]
        A3[Error Reporting Component]
        A4[Start/Stop Processing Button]
    end

    subgraph Backend Logic
        B1[File Traversal & Filtering]
        B2[Concurrency Manager (Queue)]
        B3[Database Interaction Layer]
        B4[LLM API Client]
        B5[Polling Mechanism]
        B6[Error Handling & Logging]
    end

    A --> A1
    A --> A2
    A --> A3
    A --> A4

    B1 --> B2
    B2 --> B3
    B2 --> B4
    B4 --> E
    B4 --> B5
    B5 --> B3
    B6 --> A3
    B3 --> D
    C --> B1
```

### **Proposed Database Schema (Conceptual - will confirm after inspection)**

Assuming `llm_evaluation.db` is a SQLite database, here's a conceptual schema based on the requirements. I will confirm and refine this after inspecting the actual database.

```sql
-- llm_configurations table
CREATE TABLE llm_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_type TEXT NOT NULL, -- e.g., "openai", "ollama", "lmstudio"
    url TEXT NOT NULL,
    port_no INTEGER,
    model_name TEXT,
    api_key TEXT,
    deployment_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- prompt table
CREATE TABLE prompt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_text TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- documents table
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL, -- e.g., "pdf", "txt", "docx", "xlsx"
    llm_config_id INTEGER NOT NULL,
    prompt_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'R', -- 'R' (Ready), 'F' (Failure), 'S' (Success), 'P' (Processing)
    task_id TEXT, -- Task ID from analyze_document_with_llm API
    started_processing_at TIMESTAMP,
    completed_processing_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (llm_config_id) REFERENCES llm_configurations(id),
    FOREIGN KEY (prompt_id) REFERENCES prompt(id)
);

-- llm_response table
CREATE TABLE llm_response (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    llm_config_id INTEGER NOT NULL,
    prompt_id INTEGER NOT NULL,
    response_text TEXT,
    status TEXT NOT NULL, -- 'S' (Success), 'F' (Failure)
    error_message TEXT,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id),
    FOREIGN KEY (llm_config_id) REFERENCES llm_configurations(id),
    FOREIGN KEY (prompt_id) REFERENCES prompt(id)
);
```

### **Detailed Plan**

**Phase 1: Initial Setup & Database Inspection**

1.  **Switch to Code Mode:** Request to switch to `code` mode to allow execution of `sqlite3` command to inspect the `llm_evaluation.db` schema.
2.  **Inspect Database Schema:** Use `sqlite3 llm_evaluation.db .schema` to get the actual table schemas.
3.  **Confirm/Adjust Schema:** Based on the actual schema, confirm if the conceptual schema needs adjustments.

**Phase 2: Backend Development (Node.js/Python - TBD based on preference, but Node.js is common for React apps)**

1.  **Project Initialization:**
    *   Create a new backend project (e.g., Node.js with Express or Python with Flask/FastAPI).
    *   Install necessary dependencies (e.g., `sqlite3` driver, `multer` for file uploads, `axios`/`requests` for API calls, `chokidar` for file system watching if needed, `queue` library for concurrency).
2.  **API Endpoints:**
    *   `POST /api/process-folder`: Receives the selected folder path from the UI.
    *   `GET /api/progress`: Returns current processing progress (files processed/total, outstanding tasks).
    *   `GET /api/errors`: Returns a list of all processing errors.
    *   `GET /api/llm-configs`: Returns LLM configurations from the database.
    *   `GET /api/prompts`: Returns prompts from the database.
3.  **Core Logic:**
    *   **File Traversal:** Implement logic to recursively traverse the selected folder and identify `pdf`, `txt`, `docx`, `xlsx` files.
    *   **Database Interaction Layer:** Create functions to interact with the `llm_configurations`, `prompt`, `documents`, and `llm_response` tables (CRUD operations).
    *   **Concurrency Management:**
        *   Implement a queue (e.g., using `async` library in Node.js or `concurrent.futures` in Python) to manage concurrent LLM analysis tasks.
        *   Limit concurrent tasks to 10 outstanding documents.
    *   **LLM Analysis Workflow:**
        *   For each identified file, and for each LLM configuration and prompt:
            *   Insert a new record into the `documents` table with status 'R' (Ready).
            *   Add a task to the concurrency queue.
            *   When a task starts:
                *   Update `documents` status to 'P' (Processing) and record `started_processing_at`.
                *   Call `/analyze_document_with_llm` API with the file, filename, prompts (JSON string), and LLM provider (JSON string).
                *   Store the `task_id` received from the API in the `documents` table.
                *   Start a polling mechanism for this `task_id`.
    *   **Polling Mechanism:**
        *   Periodically call `/analyze_status/{task_id}` using the `task_id` from the `documents` table.
        *   If the status is not received within 5 minutes, mark the document as 'F' (Failure) in the `documents` table and record an error message.
        *   Once the analysis is complete (status indicates success or failure):
            *   Update the `documents` table with the final status ('S' or 'F') and `completed_processing_at`.
            *   If successful, parse the `results` from the `analyze_status` response and insert records into the `llm_response` table.
            *   If failed, record the `error_message` in the `documents` table and `llm_response` table.
    *   **Error Handling & Logging:** Implement robust error handling for file operations, database interactions, and API calls. Log errors for debugging.

**Phase 3: Frontend Development (React)**

1.  **Project Initialization:**
    *   Create a new React project (e.g., using Create React App or Vite).
    *   Install necessary dependencies (e.g., `axios` for API calls, a UI library like Material-UI or Ant Design for components, `react-router-dom` if multiple views are needed).
2.  **Components:**
    *   **Main Application Component:** Orchestrates the overall UI.
    *   **Folder Selection Component:**
        *   Provides a button to trigger a native file dialog. For a web application, this typically means the user selects files for upload. To allow selecting a *folder* on the local machine for backend processing, this implies a local backend service that has file system access. The UI will send the *path string* to the backend, and the backend will handle the actual folder traversal.
        *   Displays the selected folder path.
    *   **Progress Display Component:**
        *   Displays "Files Processed: X / Total Files: Y".
        *   Displays "Outstanding Documents: Z".
    *   **Error Button & Modal:**
        *   A button labeled "Errors" that is enabled if there are any errors.
        *   Clicking the button opens a modal dialog displaying a list of errors (e.g., file path, error message, timestamp).
    *   **LLM Configuration and Prompt Selection (Optional but Recommended):**
        *   Components to display and allow selection of LLM configurations and prompts from the database, if the user wants to dynamically choose them.
3.  **State Management:** Use React's `useState` and `useEffect` hooks, or a state management library (e.g., Redux, Zustand) for more complex state.
4.  **API Integration:**
    *   Call backend API endpoints (`/api/process-folder`, `/api/progress`, `/api/errors`, etc.).
    *   Use WebSockets or long polling for real-time progress updates from the backend.

**Phase 4: Deployment & Testing**

1.  **Local Development Setup:** Instructions for running the backend and frontend locally.
2.  **Testing:** Unit tests for backend logic, integration tests for API interactions, and end-to-end tests for the UI.