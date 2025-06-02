#!/usr/bin/env python3
"""Test base64 encoding issue with PostgreSQL"""

import base64

# The error message says: "Invalid base64-encoded string: number of data characters (1398101) cannot be 1 more than a multiple of 4"
# This is a PostgreSQL error when trying to decode base64

# Standard base64.b64encode in Python ALWAYS produces valid base64 with proper padding
# So the issue must be either:
# 1. The content column in PostgreSQL expects decoded bytes, not base64 string
# 2. There's some PostgreSQL function trying to decode the base64
# 3. The data is being double-encoded or corrupted somehow

print("Understanding the issue:")
print("1. Python's base64.b64encode ALWAYS produces valid base64")
print("2. The error comes from PostgreSQL, not Python")
print("3. PostgreSQL is complaining about base64 validation")
print("\nThis suggests the 'content' column might have a CHECK constraint or")
print("the column type might be bytea with automatic base64 decoding")

# Let's check what happens with a file that produces this exact size
target_file_size = 1048575  # This produces 1398100 base64 chars
test_content = b'X' * target_file_size

encoded = base64.b64encode(test_content).decode('utf-8')
print(f"\nTest file size: {len(test_content)} bytes")
print(f"Base64 encoded length: {len(encoded)} characters")
print(f"Length mod 4: {len(encoded) % 4}")
print(f"First 50 chars: {encoded[:50]}")
print(f"Last 50 chars: {encoded[-50:]}")

# The Python encoding is fine. The issue is in PostgreSQL.
print("\nThe issue is likely that the PostgreSQL 'content' column:")
print("1. Is defined as bytea type")
print("2. PostgreSQL is automatically trying to decode base64 input")
print("3. There's an extra character being added somewhere (newline?)")

print("\nPossible solutions:")
print("1. Check the actual column type in KnowledgeDocuments.docs table")
print("2. Use bytea literal format: E'\\\\x' || encode(data, 'hex')")
print("3. Or ensure no extra characters are added to the base64 string")