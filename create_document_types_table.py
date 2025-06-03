#!/usr/bin/env python3
"""
Create document_types table and populate with valid file types
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os

# Database configuration
DB_CONFIG = {
    'host': 'studio.local',
    'port': 5432,
    'database': 'doc_eval',
    'user': 'postgres',
    'password': 'prodogs03'
}

def create_document_types_table():
    """Create the document_types table and populate with initial data"""
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("Creating document_types table...")
        
        # Create the table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS document_types (
            id SERIAL PRIMARY KEY,
            file_extension VARCHAR(10) NOT NULL UNIQUE,
            mime_type VARCHAR(100),
            description VARCHAR(255),
            is_valid BOOLEAN DEFAULT TRUE,
            supports_text_extraction BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cursor.execute(create_table_sql)
        
        # Create index for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_document_types_extension ON document_types(file_extension);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_document_types_valid ON document_types(is_valid);")
        
        print("Table created successfully.")
        
        # Insert initial valid document types
        print("Inserting initial document types...")
        
        document_types = [
            # Text formats
            ('.txt', 'text/plain', 'Plain text file', True, True),
            ('.md', 'text/markdown', 'Markdown file', True, True),
            ('.rtf', 'application/rtf', 'Rich Text Format', True, True),
            
            # Microsoft Office
            ('.doc', 'application/msword', 'Microsoft Word 97-2003', True, True),
            ('.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'Microsoft Word 2007+', True, True),
            ('.xls', 'application/vnd.ms-excel', 'Microsoft Excel 97-2003', True, True),
            ('.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Microsoft Excel 2007+', True, True),
            ('.ppt', 'application/vnd.ms-powerpoint', 'Microsoft PowerPoint 97-2003', True, True),
            ('.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'Microsoft PowerPoint 2007+', True, True),
            
            # OpenDocument formats
            ('.odt', 'application/vnd.oasis.opendocument.text', 'OpenDocument Text', True, True),
            ('.ods', 've.oasis.opendocument.spreadsheet', 'OpenDocument Spreadsheet', True, True),
            ('.odp', 'application/vnd.oasis.opendocument.presentation', 'OpenDocument Presentation', True, True),
            
            # PDF
            ('.pdf', 'application/pdf', 'Portable Document Format', True, True),
            
            # HTML/XML
            ('.html', 'text/html', 'HTML document', True, True),
            ('.htm', 'text/html', 'HTML document', True, True),
            ('.xml', 'application/xml', 'XML document', True, True),
            
            # Code files
            ('.py', 'text/x-python', 'Python source code', True, True),
            ('.js', 'application/javascript', 'JavaScript source code', True, True),
            ('.java', 'text/x-java-source', 'Java source code', True, True),
            ('.cpp', 'text/x-c++src', 'C++ source code', True, True),
            ('.c', 'text/x-csrc', 'C source code', True, True),
            ('.h', 'text/x-chdr', 'C/C++ header file', True, True),
            ('.cs', 'text/x-csharp', 'C# source code', True, True),
            ('.php', 'application/x-httpd-php', 'PHP source code', True, True),
            ('.rb', 'application/x-ruby', 'Ruby source code', True, True),
            ('.go', 'text/x-go', 'Go source code', True, True),
            ('.rs', 'text/x-rust', 'Rust source code', True, True),
            
            # Configuration files
            ('.json', 'application/json', 'JSON file', True, True),
            ('.yaml', 'application/x-yaml', 'YAML file', True, True),
            ('.yml', 'application/x-yaml', 'YAML file', True, True),
            ('.toml', 'application/toml', 'TOML file', True, True),
            ('.ini', 'text/plain', 'INI configuration file', True, True),
            ('.conf', 'text/plain', 'Configuration file', True, True),
            ('.cfg', 'text/plain', 'Configuration file', True, True),
            
            # Log files
            ('.log', 'text/plain', 'Log file', True, True),
            
            # CSV and data files
            ('.csv', 'text/csv', 'Comma-separated values', True, True),
            ('.tsv', 'text/tab-separated-values', 'Tab-separated values', True, True),
            
            # Common invalid/unsupported types (for reference)
            ('.exe', 'application/x-msdownload', 'Executable file', False, False),
            ('.dll', 'application/x-msdownload', 'Dynamic Link Library', False, False),
            ('.bin', 'application/octet-stream', 'Binary file', False, False),
            ('.zip', 'application/zip', 'ZIP archive', False, False),
            ('.rar', 'application/x-rar-compressed', 'RAR archive', False, False),
            ('.7z', 'application/x-7z-compressed', '7-Zip archive', False, False),
            ('.tar', 'application/x-tar', 'TAR archive', False, False),
            ('.gz', 'application/gzip', 'Gzip compressed file', False, False),
            ('.mp3', 'audio/mpeg', 'MP3 audio file', False, False),
            ('.mp4', 'video/mp4', 'MP4 video file', False, False),
            ('.avi', 'video/x-msvideo', 'AVI video file', False, False),
            ('.jpg', 'image/jpeg', 'JPEG image', False, False),
            ('.jpeg', 'image/jpeg', 'JPEG image', False, False),
            ('.png', 'image/png', 'PNG image', False, False),
            ('.gif', 'image/gif', 'GIF image', False, False),
            ('.bmp', 'image/bmp', 'Bitmap image', False, False),
            ('.ico', 'image/x-icon', 'Icon file', False, False),
        ]
        
        insert_sql = """
        INSERT INTO document_types (file_extension, mime_type, description, is_valid, supports_text_extraction)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (file_extension) DO UPDATE SET
            mime_type = EXCLUDED.mime_type,
            description = EXCLUDED.description,
            is_valid = EXCLUDED.is_valid,
            supports_text_extraction = EXCLUDED.supports_text_extraction,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        cursor.executemany(insert_sql, document_types)
        
        # Commit changes
        conn.commit()
        
        print(f"Successfully inserted {len(document_types)} document types.")
        
        # Display results
        cursor.execute("SELECT file_extension, description, is_valid FROM document_types ORDER BY is_valid DESC, file_extension;")
        results = cursor.fetchall()
        
        print("\nDocument types in database:")
        print("-" * 60)
        
        valid_count = 0
        invalid_count = 0
        
        for row in results:
            status = "✅ VALID" if row['is_valid'] else "❌ INVALID"
            print(f"{row['file_extension']:<8} {status:<10} {row['description']}")
            
            if row['is_valid']:
                valid_count += 1
            else:
                invalid_count += 1
        
        print("-" * 60)
        print(f"Total: {len(results)} types ({valid_count} valid, {invalid_count} invalid)")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Document types table created and populated successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_document_types_table()