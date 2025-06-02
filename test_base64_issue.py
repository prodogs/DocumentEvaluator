#!/usr/bin/env python3
"""Test base64 encoding issue with specific size"""

import base64

# The problematic size from the error message
problematic_size = 1398101

print(f"Problematic encoded size: {problematic_size} characters")
print(f"This number mod 4 = {problematic_size % 4}")
print(f"This means the base64 string has 1 extra character that shouldn't be there\n")

# Calculate the expected original file size
# Base64 encoding increases size by ~33% (4 chars for every 3 bytes)
# So original size = encoded_size * 3 / 4
expected_original_size = (problematic_size * 3) // 4
print(f"Expected original file size: ~{expected_original_size} bytes ({expected_original_size / 1024 / 1024:.2f} MB)")

# Check if it's actually 1398100 chars (divisible by 4) with an extra character
correct_size = 1398100
print(f"\nIf the correct size is {correct_size} (divisible by 4):")
print(f"Original file size would be: {(correct_size * 3) // 4} bytes ({(correct_size * 3) // 4 / 1024 / 1024:.2f} MB)")

# Common causes:
print("\nPossible causes of this error:")
print("1. The content is already base64 encoded and being encoded again (double encoding)")
print("2. There's an extra character added to the base64 string (newline, space, etc.)")
print("3. The base64 string is being truncated incorrectly")
print("4. The content being encoded has been modified/corrupted")

# Check the KnowledgeDocuments database
print("\nChecking for existing entries in KnowledgeDocuments database...")
print("The error occurs when trying to decode content that's 1398101 characters")
print("This suggests the content in the 'docs' table might already be corrupted")