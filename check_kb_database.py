#!/usr/bin/env python3
"""Check KnowledgeDocuments database for the problematic document"""

# This is exactly 1MB file which results in 1398101 base64 characters with a newline
# Let's check if this document already exists in the KnowledgeDocuments database

print("Checking for documents with batch_70 pattern in KnowledgeDocuments database...")
print("\nThe error suggests a document with content length 1398101 exists")
print("This is likely a 1MB file that has been base64 encoded")
print("\nPossible document IDs to check:")
print("- batch_70_doc_* (pattern for batch 70 documents)")

# The issue is likely that:
# 1. A document was previously inserted with incorrect encoding
# 2. The batch is trying to reprocess and hitting the existing corrupted entry
# 3. Or the file being encoded has exactly 1048575 bytes + 1 extra byte

print("\nSolution options:")
print("1. Check if documents with batch_70 pattern exist in KnowledgeDocuments.docs table")
print("2. Delete any corrupted entries")
print("3. Fix the encoding logic to handle edge cases")
print("4. Add validation before inserting into database")

print("\nSQL to check in KnowledgeDocuments database:")
print("""
SELECT id, document_id, LENGTH(content) as content_length, file_size, created_at
FROM docs
WHERE document_id LIKE 'batch_70_%'
ORDER BY created_at DESC;
""")