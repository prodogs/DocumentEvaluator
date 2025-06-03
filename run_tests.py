#!/usr/bin/env python3
"""
Rerunnable Test Suite for DocumentEvaluator
Run this anytime to verify system health and functionality
"""

import sys
import time
import requests
from datetime import datetime
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

BASE_URL = "http://localhost:5001"
TESTS_PASSED = 0
TESTS_FAILED = 0

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Style.RESET_ALL}\n")

def print_test(name, passed, message=""):
    """Print test result"""
    global TESTS_PASSED, TESTS_FAILED
    if passed:
        TESTS_PASSED += 1
        print(f"{Fore.GREEN}✓{Style.RESET_ALL} {name}")
        if message:
            print(f"  {Fore.LIGHTBLACK_EX}{message}{Style.RESET_ALL}")
    else:
        TESTS_FAILED += 1
        print(f"{Fore.RED}✗{Style.RESET_ALL} {name}")
        if message:
            print(f"  {Fore.YELLOW}{message}{Style.RESET_ALL}")

def test_server_running():
    """Test 1: Check if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=2)
        return response.status_code == 200, "Server is responsive"
    except:
        return False, "Server is not running on port 5001"

def test_database_connections():
    """Test 2: Check database connections"""
    try:
        response = requests.get(f"{BASE_URL}/api/health/detailed", timeout=5)
        if response.status_code != 200:
            return False, f"Health check returned {response.status_code}"
        
        data = response.json()
        services = data.get('services', {})
        
        # Check KnowledgeSync database (main application database)
        knowledgesync_db = services.get('knowledgesync_database', {})
        if knowledgesync_db.get('status') != 'healthy':
            return False, f"KnowledgeSync database is {knowledgesync_db.get('status', 'unknown')}"
        
        # Check knowledge database
        knowledge_db = services.get('knowledge_database', {})
        if knowledge_db.get('status') != 'healthy':
            return False, f"Knowledge database is {knowledge_db.get('status', 'unknown')}"
        
        return True, "Both databases are healthy"
    except Exception as e:
        return False, f"Error checking databases: {str(e)}"

def test_critical_endpoints():
    """Test 3: Check critical API endpoints"""
    endpoints = [
        ('/api/batches', 'Batch listing'),
        ('/api/folders', 'Folder listing'),
        ('/api/connections', 'Connection listing'),
        ('/api/prompts', 'Prompt listing'),
        ('/api/dashboard', 'Dashboard data')
    ]
    
    failed = []
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            if response.status_code != 200:
                failed.append(f"{name} ({endpoint}): {response.status_code}")
        except Exception as e:
            failed.append(f"{name} ({endpoint}): {str(e)}")
    
    if failed:
        return False, f"{len(failed)} endpoints failed: " + ", ".join(failed)
    return True, f"All {len(endpoints)} critical endpoints are working"

def test_system_health_status():
    """Test 4: Check overall system health"""
    try:
        response = requests.get(f"{BASE_URL}/api/dashboard", timeout=5)
        if response.status_code != 200:
            return False, f"Dashboard returned {response.status_code}"
        
        data = response.json()
        health_status = data.get('health', {}).get('status', 'unknown')
        
        if health_status == 'healthy':
            return True, "System is healthy"
        elif health_status == 'degraded':
            issues = data.get('health', {}).get('issues', [])
            return True, f"System is degraded: {', '.join(issues)}"
        else:
            return False, f"System is {health_status}"
    except Exception as e:
        return False, f"Error checking system health: {str(e)}"

def test_batch_metrics():
    """Test 5: Check batch processing metrics"""
    try:
        response = requests.get(f"{BASE_URL}/api/metrics/batches", timeout=5)
        if response.status_code != 200:
            return False, f"Batch metrics returned {response.status_code}"
        
        data = response.json()
        last_24h = data.get('last_24_hours', {})
        
        total = last_24h.get('total', 0)
        failed = last_24h.get('failed', 0)
        failure_rate = last_24h.get('failure_rate', 0)
        
        message = f"Last 24h: {total} batches, {failed} failed ({failure_rate}% failure rate)"
        
        if failure_rate > 50:
            return False, f"High failure rate! {message}"
        elif failure_rate > 20:
            return True, f"Warning: {message}"
        else:
            return True, message
    except Exception as e:
        return False, f"Error checking batch metrics: {str(e)}"

def test_queue_status():
    """Test 6: Check processing queue"""
    try:
        response = requests.get(f"{BASE_URL}/api/metrics/processing-queue", timeout=5)
        if response.status_code != 200:
            return False, f"Queue metrics returned {response.status_code}"
        
        data = response.json()
        alerts = data.get('alerts', {})
        stuck = alerts.get('stuck_processing', 0)
        
        last_hour = data.get('last_hour', {})
        queued = last_hour.get('queued', 0)
        processing = last_hour.get('processing', 0)
        completed = last_hour.get('completed', 0)
        
        message = f"Queue: {queued} queued, {processing} processing, {completed} completed/hr"
        
        if stuck > 0:
            return False, f"{stuck} items stuck! {message}"
        else:
            return True, message
    except Exception as e:
        return False, f"Error checking queue: {str(e)}"

def test_llm_config_formatter():
    """Test 7: Check LLM config formatter (if available)"""
    try:
        sys.path.append('/Users/frankfilippis/AI/Github/DocumentEvaluator/server')
        from utils.llm_config_formatter import format_llm_config_for_rag_api
        
        test_config = {
            'provider_type': 'ollama',
            'base_url': 'http://localhost',
            'port_no': 11434,
            'model_name': 'test-model'
        }
        
        result = format_llm_config_for_rag_api(test_config)
        
        if 'base_url' not in result:
            return False, "Formatter missing 'base_url' field"
        if result['base_url'] != 'http://localhost:11434':
            return False, f"Incorrect URL formatting: {result['base_url']}"
        
        return True, "LLM config formatter working correctly"
    except ImportError:
        return True, "LLM config formatter not available (skipped)"
    except Exception as e:
        return False, f"Formatter error: {str(e)}"

def test_response_times():
    """Test 8: Check API response times"""
    endpoints = [
        ('/api/health', 100),  # Should respond in 100ms
        ('/api/dashboard', 500),  # Dashboard can take longer
    ]
    
    slow_endpoints = []
    for endpoint, max_ms in endpoints:
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            duration_ms = (time.time() - start) * 1000
            
            if duration_ms > max_ms:
                slow_endpoints.append(f"{endpoint}: {duration_ms:.0f}ms (max: {max_ms}ms)")
        except:
            slow_endpoints.append(f"{endpoint}: timeout")
    
    if slow_endpoints:
        return False, "Slow endpoints: " + ", ".join(slow_endpoints)
    return True, "All endpoints responding quickly"

def main():
    """Run all tests"""
    print(f"\n{Fore.CYAN}DocumentEvaluator Test Suite{Style.RESET_ALL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Server: {BASE_URL}")
    
    # Check if server is running first
    print_header("Connectivity Tests")
    passed, message = test_server_running()
    print_test("Server Running", passed, message)
    
    if not passed:
        print(f"\n{Fore.RED}Cannot run remaining tests - server is not running!{Style.RESET_ALL}")
        print(f"Start the server with: cd server && python app.py")
        sys.exit(1)
    
    # Run remaining tests
    print_header("Infrastructure Tests")
    passed, message = test_database_connections()
    print_test("Database Connections", passed, message)
    
    passed, message = test_critical_endpoints()
    print_test("API Endpoints", passed, message)
    
    print_header("Health & Performance Tests")
    passed, message = test_system_health_status()
    print_test("System Health", passed, message)
    
    passed, message = test_response_times()
    print_test("Response Times", passed, message)
    
    print_header("Business Logic Tests")
    passed, message = test_batch_metrics()
    print_test("Batch Processing", passed, message)
    
    passed, message = test_queue_status()
    print_test("Queue Status", passed, message)
    
    passed, message = test_llm_config_formatter()
    print_test("LLM Config Formatter", passed, message)
    
    # Summary
    print_header("Test Summary")
    total_tests = TESTS_PASSED + TESTS_FAILED
    success_rate = (TESTS_PASSED / total_tests * 100) if total_tests > 0 else 0
    
    if TESTS_FAILED == 0:
        print(f"{Fore.GREEN}✅ ALL TESTS PASSED! ({TESTS_PASSED}/{total_tests}){Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}⚠️  {TESTS_FAILED} tests failed ({TESTS_PASSED}/{total_tests} passed, {success_rate:.1f}% success rate){Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}View detailed monitoring at: {BASE_URL}/static/monitor.html{Style.RESET_ALL}")
    
    # Exit with appropriate code
    sys.exit(0 if TESTS_FAILED == 0 else 1)

if __name__ == "__main__":
    main()