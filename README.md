# Document Batch Processor

A comprehensive document analysis system that processes documents in batches using configurable LLM (Large Language Model) services. The system provides a two-stage batch processing workflow with real-time monitoring and progress tracking.

## 🚀 Features

### Core Functionality
- **Two-Stage Batch Processing**: Create batches in "PREPARED" state, then execute when ready
- **Document Encoding**: Automatic document encoding and storage in database
- **Real-time Monitoring**: Live progress tracking with processing statistics
- **Batch Management**: Create, pause, resume, and delete batches
- **Service Recovery**: Automatic recovery of outstanding tasks on service restart

### Configuration Management
- **LLM Configurations**: Manage multiple LLM service endpoints
- **Prompts**: Create and manage reusable prompts
- **Folders**: Configure document source folders
- **Metadata Support**: JSON metadata for batches and documents

### Dashboard & Analytics
- **System Overview**: Real-time processing statistics
- **Batch Progress**: Detailed progress tracking per batch
- **Success Rates**: Processing success/failure analytics
- **Response Times**: Performance monitoring

## Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL
- Git

### Backend Setup

1. Clone repository and setup environment:

```bash
git clone <repository-url>
cd DocumentEvaluator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

2. Configure database connection (PostgreSQL):

```bash
# Database: tablemini.local:5432/doc_eval
# User: postgres
# Password: prodogs03
```

3. Start the backend server:

```bash
python main.py
```

The backend will run on `http://localhost:5001`

### Frontend Setup

1. Install dependencies:

```bash
cd client
npm install
```

2. Configure environment:

```bash
# .env file already configured for:
# VITE_API_URL=http://localhost:5001
```

3. Start the development server:

```bash
npm run dev
```

The frontend will run on `http://localhost:5173`

## Usage

### 1. Setup Configuration
1. **LLM Configurations**: Add your LLM service endpoints in the management tab
2. **Prompts**: Create reusable prompts for document analysis
3. **Folders**: Configure document source folders

### 2. Create Batch (Two-Stage Process)
1. Navigate to "Analyze Documents" tab
2. Select active LLM configurations, prompts, and folders
3. Enter batch name and metadata (JSON format)
4. Click "Start Document Analysis" → Creates PREPARED batch

### 3. Execute Batch
1. Click "Run" button to start processing
2. Monitor progress in real-time on Dashboard
3. View detailed results and statistics

### 4. Monitor & Manage
- **Dashboard**: View system overview and batch statistics
- **Batch Management**: Pause, resume, or delete batches
- **Archive**: Deleted batches are archived with full data preservation

## 🏗️ Architecture

### Backend (Python/Flask)
- **API Server**: RESTful API on port 5001
- **Database**: PostgreSQL with comprehensive schema
- **Services**: Dynamic processing queue, health monitoring, batch cleanup
- **Document Processing**: File encoding, MIME type detection, LLM integration

### Frontend (React/Vite)
- **Modern UI**: React-based interface with real-time updates
- **Responsive Design**: Full browser space utilization
- **Tab-based Navigation**: Dashboard, Analyze Documents, Management tabs

### Database Schema (PostgreSQL)
- **batches**: Batch configuration and metadata
- **documents**: Document records with encoding
- **docs**: Encoded document storage with type detection
- **llm_responses**: Processing results and analytics
- **llm_configurations**: LLM service settings
- **prompts**: Reusable prompt templates
- **folders**: Document source configuration
- **batch_archive**: Archived batch data

## 📊 Key Features

### Two-Stage Processing
1. **Stage 1 (Preparation)**: Creates batch, encodes documents, validates configuration
2. **Stage 2 (Execution)**: User-initiated processing with real-time monitoring

### Real-time Monitoring
- Processing queue status (30 concurrent slots)
- Batch progress with success/failure rates
- Average processing times
- System health monitoring

## 🔧 API Documentation

API documentation available at `http://localhost:5001/api/docs`

### Key Endpoints
- `GET /api/folders` - List configured folders
- `GET /api/llm-configurations` - List LLM configurations
- `GET /api/prompts` - List available prompts
- `POST /api/batches` - Create new batch
- `POST /api/batches/{id}/run` - Execute batch
- `GET /api/batches/dashboard` - Dashboard data

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

MIT License - see LICENSE file for details.
