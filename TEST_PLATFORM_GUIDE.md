# Test Platform Guide for DocumentEvaluator

## Overview of Test Files Created

### 1. One-Time Verification Tests
These were created to verify specific fixes and aren't meant for regular use:

- **`test_complete_workflow.py`** - Comprehensive test that tries to create new batches
  - ❌ NOT rerunnable (tries to stage documents that may already be assigned)
  - Purpose: Verify all systems work after major changes
  - When to use: After major refactoring only

- **`cleanup_duplicate_llm_responses.py`** - Database cleanup script
  - ⚠️  Destructive operation (deletes duplicates)
  - Purpose: Fix specific data issues
  - When to use: Only when duplicates are detected

### 2. Reusable Test Platform
These are designed for continuous testing:

- **`test_key_changes.py`** - Focused integration tests
  - ✅ FULLY RERUNNABLE
  - Non-destructive (only reads data)
  - Tests core functionality without side effects
  - When to use: After any code changes, before commits

### 3. Monitoring Platform (New)
The monitoring system IS a test platform:

- **`/api/health/detailed`** - Real-time health checks
- **`/api/dashboard`** - Combined system metrics
- **`/static/monitor.html`** - Visual monitoring dashboard
  - ✅ Always available
  - Real-time system status
  - When to use: Continuously during development

## Building a Proper Test Platform

Here's what we should add for a complete test platform:

### A. Unit Test Suite
```python
# tests/test_unit_batch_service.py
import pytest
from unittest.mock import Mock, patch
from services.batch_service import BatchService

class TestBatchService:
    def test_validate_batch_data(self):
        """Test batch data validation"""
        # Test valid data
        valid_data = {
            'folder_ids': [1, 2],
            'connection_ids': [1],
            'prompt_ids': [1, 2, 3]
        }
        assert BatchService._validate_batch_data(valid_data) == True
        
    def test_validate_batch_data_missing_fields(self):
        """Test validation with missing fields"""
        invalid_data = {'folder_ids': [1]}
        with pytest.raises(ValueError):
            BatchService._validate_batch_data(invalid_data)
```

### B. Integration Test Suite
```python
# tests/test_integration.py
import pytest
from test_fixtures import test_database, test_client

class TestBatchWorkflow:
    def test_staging_creates_llm_responses(self, test_database):
        """Test that staging creates llm_responses correctly"""
        # Use test database with known data
        pass
        
    def test_no_duplicate_responses(self, test_database):
        """Test that re-running doesn't create duplicates"""
        pass
```

### C. Load Test Suite
```python
# tests/test_load.py
import asyncio
import aiohttp
from datetime import datetime

class LoadTester:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.results = []
    
    async def test_concurrent_batches(self, num_batches=10):
        """Test system under concurrent load"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(num_batches):
                task = self.create_and_run_batch(session, i)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            self.analyze_results(results)
    
    async def create_and_run_batch(self, session, batch_num):
        """Create and run a single batch"""
        start_time = datetime.now()
        try:
            # Stage batch
            async with session.post(f"{self.base_url}/api/batches/stage", 
                                   json=self.get_test_batch_data(batch_num)) as resp:
                stage_result = await resp.json()
            
            # Run batch
            batch_id = stage_result['batch_id']
            async with session.post(f"{self.base_url}/api/batches/{batch_id}/run") as resp:
                run_result = await resp.json()
            
            duration = (datetime.now() - start_time).total_seconds()
            return {
                'batch_num': batch_num,
                'success': True,
                'duration': duration
            }
        except Exception as e:
            return {
                'batch_num': batch_num,
                'success': False,
                'error': str(e)
            }
```

### D. Continuous Testing Script
```python
# tests/continuous_test.py
#!/usr/bin/env python3
"""
Continuous testing script that runs in the background
and alerts on failures.
"""

import time
import requests
import logging
from datetime import datetime

class ContinuousMonitor:
    def __init__(self, base_url="http://localhost:5001", interval=60):
        self.base_url = base_url
        self.interval = interval
        self.logger = logging.getLogger(__name__)
        
    def run_test_cycle(self):
        """Run one complete test cycle"""
        results = {
            'timestamp': datetime.now(),
            'health_check': self.test_health(),
            'database_check': self.test_databases(),
            'api_check': self.test_critical_apis(),
            'performance_check': self.test_response_times()
        }
        
        # Alert if any failures
        failures = [k for k, v in results.items() if v.get('success') == False]
        if failures:
            self.alert_failures(failures, results)
        
        return results
    
    def test_health(self):
        """Test system health"""
        try:
            resp = requests.get(f"{self.base_url}/api/health/detailed", timeout=5)
            data = resp.json()
            return {
                'success': data['status'] == 'healthy',
                'status': data['status'],
                'issues': data.get('issues', [])
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def run_forever(self):
        """Run continuous monitoring"""
        self.logger.info("Starting continuous monitoring...")
        while True:
            try:
                results = self.run_test_cycle()
                self.logger.info(f"Test cycle completed: {results['health_check']['status']}")
                time.sleep(self.interval)
            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Test cycle failed: {e}")
                time.sleep(self.interval)
```

### E. Test Data Generator
```python
# tests/test_data_generator.py
import os
import random
from faker import Faker

class TestDataGenerator:
    def __init__(self):
        self.fake = Faker()
        
    def create_test_documents(self, folder_path, count=10):
        """Create test documents with realistic content"""
        os.makedirs(folder_path, exist_ok=True)
        
        for i in range(count):
            content = self.generate_document_content()
            filename = f"test_doc_{i}_{self.fake.word()}.txt"
            filepath = os.path.join(folder_path, filename)
            
            with open(filepath, 'w') as f:
                f.write(content)
        
        return folder_path
    
    def generate_document_content(self):
        """Generate realistic document content"""
        return f"""
        {self.fake.company()} - {self.fake.catch_phrase()}
        
        Date: {self.fake.date()}
        Author: {self.fake.name()}
        
        {self.fake.paragraph(nb_sentences=10)}
        
        Key Points:
        - {self.fake.sentence()}
        - {self.fake.sentence()}
        - {self.fake.sentence()}
        
        {self.fake.paragraph(nb_sentences=5)}
        """
```

## Recommended Test Platform Structure

```
DocumentEvaluator/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration and fixtures
│   ├── unit/                    # Unit tests (fast, isolated)
│   │   ├── test_batch_service.py
│   │   ├── test_staging_service.py
│   │   └── test_formatters.py
│   ├── integration/             # Integration tests (with DB)
│   │   ├── test_full_workflow.py
│   │   ├── test_api_endpoints.py
│   │   └── test_database_operations.py
│   ├── load/                    # Load and performance tests
│   │   ├── test_concurrent_batches.py
│   │   └── test_stress_test.py
│   ├── continuous/              # Continuous monitoring tests
│   │   ├── monitor.py
│   │   └── alerting.py
│   └── fixtures/                # Test data and utilities
│       ├── test_data.py
│       ├── mock_rag_api.py
│       └── database_fixtures.py
├── pytest.ini                   # Pytest configuration
├── tox.ini                      # Test automation
└── Makefile                     # Test commands

```

## Quick Test Commands

Add to your Makefile:
```makefile
# Makefile
.PHONY: test test-unit test-integration test-load test-all monitor

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v

test-load:
	python tests/load/test_concurrent_batches.py

test-key-changes:
	python test_key_changes.py

monitor:
	python tests/continuous/monitor.py

test-all: test-unit test-integration test-key-changes

test-quick:
	# Quick smoke test
	curl -s http://localhost:5001/api/health/detailed | jq .status
	python test_key_changes.py
```

## Current Status

What you have now:
1. ✅ Basic monitoring (real-time health checks)
2. ✅ Key functionality verification (`test_key_changes.py`)
3. ✅ Visual dashboard for continuous monitoring
4. ⚠️  Some one-time test scripts (not rerunnable)

What you need for a complete test platform:
1. ❌ Proper unit tests with mocking
2. ❌ Integration tests with test database
3. ❌ Load testing capabilities
4. ❌ Automated test runner (pytest + tox)
5. ❌ CI/CD integration

## Next Steps

1. **For now**: Use `test_key_changes.py` as your go-to test
   ```bash
   python test_key_changes.py  # Run this before commits
   ```

2. **Monitor continuously**: Keep the dashboard open
   ```
   http://localhost:5001/static/monitor.html
   ```

3. **When ready**: Set up proper pytest suite with fixtures