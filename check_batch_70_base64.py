#!/usr/bin/env python3
"""Check for base64 encoding issues in batch 70 documents"""

import base64
import os

def check_base64_padding(s):
    """Check if a base64 string has correct padding"""
    missing_padding = len(s) % 4
    if missing_padding:
        return False, f"Missing {4 - missing_padding} padding characters"
    return True, "Padding OK"

def fix_base64_padding(s):
    """Fix base64 padding"""
    missing_padding = len(s) % 4
    if missing_padding:
        s += '=' * (4 - missing_padding)
    return s

def check_file_encoding(filepath):
    """Check if a file can be properly base64 encoded/decoded"""
    try:
        # Read file
        with open(filepath, 'rb') as f:
            content = f.read()
        
        file_size = len(content)
        print(f"File size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
        
        # Encode
        encoded = base64.b64encode(content).decode('utf-8')
        print(f"Encoded length: {len(encoded)} characters")
        
        # Check if this is the problematic size
        if len(encoded) == 1398101:
            print("⚠️  WARNING: This file produces exactly 1398101 characters when encoded!")
        
        # Check padding
        padding_ok, padding_msg = check_base64_padding(encoded)
        print(f"Padding check: {padding_msg}")
        
        # Try to decode
        try:
            decoded = base64.b64decode(encoded)
            print(f"✅ Decode successful, decoded size: {len(decoded)} bytes")
            
            # Verify content matches
            if decoded == content:
                print("✅ Content verification passed")
            else:
                print("❌ Content verification FAILED - decoded content doesn't match original!")
                
        except Exception as e:
            print(f"❌ Decode failed: {e}")
            
            # Try with fixed padding
            print("Attempting to fix padding...")
            fixed = fix_base64_padding(encoded)
            try:
                decoded = base64.b64decode(fixed)
                print(f"✅ Decode successful with fixed padding")
            except Exception as e2:
                print(f"❌ Decode still failed after padding fix: {e2}")
                
        return True
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        return False

def main():
    # Check if we can find documents that might be problematic
    # The error mentions 1398101 characters, which would be from a file of approximately:
    # 1398101 * 3 / 4 = 1048575.75 bytes ≈ 1MB
    
    print("Checking for files around 1MB in size...")
    print("Expected file size for 1398101 base64 chars: ~1,048,576 bytes")
    print()
    
    # You can modify this to check specific files
    test_files = [
        "/Users/frankfilippis/AI/Github/DocumentEvaluator/doc/doc.pdf",
        # Add more files here if needed
    ]
    
    for filepath in test_files:
        if os.path.exists(filepath):
            print(f"\n{'='*60}")
            print(f"Checking: {filepath}")
            print('='*60)
            check_file_encoding(filepath)
        else:
            print(f"\n❌ File not found: {filepath}")

if __name__ == "__main__":
    main()