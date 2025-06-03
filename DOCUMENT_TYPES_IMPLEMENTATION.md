# Document Types System Implementation

## Overview

The Document Types system replaces hardcoded file extension validation with a database-driven approach, making the system more flexible and maintainable.

## Components

### 1. Database Table: `document_types`

```sql
CREATE TABLE document_types (
    id SERIAL PRIMARY KEY,
    file_extension VARCHAR(10) NOT NULL UNIQUE,
    mime_type VARCHAR(100),
    description VARCHAR(255),
    is_valid BOOLEAN DEFAULT TRUE,
    supports_text_extraction BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Fields:**
- `file_extension`: File extension including the dot (e.g., `.pdf`, `.docx`)
- `mime_type`: MIME type for the file format
- `description`: Human-readable description
- `is_valid`: Whether this file type should be processed
- `supports_text_extraction`: Whether text can be extracted from this type
- `created_at/updated_at`: Audit timestamps

### 2. Document Type Service (`document_type_service.py`)

**Key Features:**
- Caches valid extensions for performance
- Validates individual files and batches
- Provides detailed file type information
- Manages document type CRUD operations
- Falls back to basic types if database is unavailable

**Main Methods:**
- `get_valid_extensions()`: Returns list of valid file extensions
- `is_valid_file_type(filename)`: Checks if a file is valid for processing
- `get_file_type_info(filename)`: Returns detailed file type information
- `validate_file_batch(filenames)`: Validates multiple files at once
- `add_document_type()`: Adds new document types
- `update_document_type_validity()`: Enable/disable file types

### 3. API Endpoints (`document_type_routes.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/document-types` | Get all document types |
| GET | `/api/document-types/valid` | Get only valid document types |
| POST | `/api/document-types/validate` | Validate a list of filenames |
| GET | `/api/document-types/<extension>` | Get info for specific extension |
| POST | `/api/document-types` | Add new document type |
| PUT | `/api/document-types/<extension>/validity` | Update validity |
| POST | `/api/document-types/refresh-cache` | Refresh cache |

### 4. Integration Points

**Folder Preprocessing Service:**
- Updated `_validate_file()` to use `document_type_service.is_valid_file_type()`
- Provides better error messages with file type descriptions

**Batch Service:**
- Already uses preprocessing validation, so inherits the new system
- Only processes documents marked as `valid='Y'` during preprocessing

## Default Supported File Types

### Valid Types (37 total)

**Text Formats:**
- `.txt` - Plain text file
- `.md` - Markdown file  
- `.rtf` - Rich Text Format

**Microsoft Office:**
- `.doc/.docx` - Microsoft Word
- `.xls/.xlsx` - Microsoft Excel
- `.ppt/.pptx` - Microsoft PowerPoint

**OpenDocument:**
- `.odt` - OpenDocument Text
- `.ods` - OpenDocument Spreadsheet
- `.odp` - OpenDocument Presentation

**PDF:**
- `.pdf` - Portable Document Format

**Code Files:**
- `.py`, `.js`, `.java`, `.cpp`, `.c`, `.h`, `.cs`, `.php`, `.rb`, `.go`, `.rs`

**Data Formats:**
- `.json`, `.yaml/.yml`, `.csv`, `.xml`, `.html/.htm`

**Configuration:**
- `.ini`, `.conf`, `.cfg`, `.toml`

**Logs:**
- `.log`

### Invalid Types (17 total)

Common invalid types are stored for reference:
- Archives: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`
- Executables: `.exe`, `.dll`, `.bin`
- Media: `.mp3`, `.mp4`, `.avi`, `.jpg`, `.png`, `.gif`, `.bmp`

## Setup Instructions

### 1. Create the Database Table

```bash
cd /path/to/DocumentEvaluator
python create_document_types_table.py
```

This script:
- Creates the `document_types` table
- Populates it with 54 predefined file types
- Shows a summary of valid/invalid types

### 2. Update Server Configuration

The document type routes are automatically registered in `app.py`:

```python
from api.document_type_routes import document_type_bp
app.register_blueprint(document_type_bp)
```

### 3. Test the Implementation

```bash
# Test the service directly
python test_document_types.py

# Test the API endpoints (requires running server)
python test_document_type_api.py
```

## Usage Examples

### Validate Files in Code

```python
from services.document_type_service import document_type_service

# Check single file
is_valid = document_type_service.is_valid_file_type("document.pdf")

# Get detailed info
info = document_type_service.get_file_type_info("document.pdf")
print(f"Extension: {info['extension']}")
print(f"Valid: {info['is_valid']}")
print(f"Description: {info['description']}")

# Validate multiple files
filenames = ["doc.pdf", "image.jpg", "code.py"]
valid_files, invalid_files = document_type_service.validate_file_batch(filenames)
```

### API Usage

```bash
# Get all valid extensions
curl -X GET "http://localhost:5001/api/document-types/valid"

# Validate files
curl -X POST "http://localhost:5001/api/document-types/validate" \
  -H "Content-Type: application/json" \
  -d '{"filenames": ["doc.pdf", "image.jpg"]}'

# Add new document type
curl -X POST "http://localhost:5001/api/document-types" \
  -H "Content-Type: application/json" \
  -d '{
    "extension": ".new",
    "mime_type": "application/new",
    "description": "New file type",
    "is_valid": true
  }'
```

## Administrative Tasks

### Adding New File Types

```sql
INSERT INTO document_types (file_extension, mime_type, description, is_valid, supports_text_extraction)
VALUES ('.epub', 'application/epub+zip', 'EPUB e-book', true, true);
```

### Disabling File Types

```sql
UPDATE document_types 
SET is_valid = false, updated_at = CURRENT_TIMESTAMP
WHERE file_extension = '.docx';
```

### View Current Configuration

```sql
SELECT file_extension, description, is_valid, supports_text_extraction
FROM document_types 
ORDER BY is_valid DESC, file_extension;
```

## Migration from Hardcoded System

The system automatically migrates from the old hardcoded `VALID_EXTENSIONS` approach:

1. **Before:** File validation checked against a hardcoded set in `FolderPreprocessingService.VALID_EXTENSIONS`
2. **After:** File validation uses database-driven `document_type_service.is_valid_file_type()`

The new system is backward compatible and provides better error messages and flexibility.

## Performance Considerations

- **Caching:** Valid extensions are cached in memory after first database query
- **Fallback:** If database is unavailable, falls back to basic file types
- **Batch Operations:** Efficient batch validation reduces database queries

## Future Enhancements

1. **Custom File Type Processing:** Different processing pipelines per file type
2. **File Size Limits per Type:** Different size limits for different file types  
3. **Content-Based Validation:** Validate file content matches declared type
4. **Admin UI:** Web interface for managing document types
5. **Import/Export:** Backup and restore document type configurations

## Troubleshooting

### Database Connection Issues
If database is unavailable, the service falls back to basic types:
- `.txt`, `.pdf`, `.docx`, `.doc`

### Cache Issues
Refresh the cache manually:
```python
document_type_service._valid_extensions_cache = None
document_type_service._refresh_cache()
```

Or via API:
```bash
curl -X POST "http://localhost:5001/api/document-types/refresh-cache"
```

### Adding Support for New File Types
1. Add to database via API or SQL
2. Refresh cache
3. Test validation with new files

This system provides a robust, flexible foundation for managing supported document types in the DocumentEvaluator system.