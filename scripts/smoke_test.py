#!/usr/bin/env python3
"""
Smoke Test Script for NutriTrack Cloud Run Deployment

Tests key endpoints on a deployed instance to verify the application is working.

Usage:
    NUTRITRACK_URL=https://your-service.run.app python scripts/smoke_test.py

Environment Variables:
    NUTRITRACK_URL  Base URL of the deployed service (required)
                    Example: https://nutritrack-abc123.run.app
"""

import os
import sys
import json
import requests
from urllib.parse import urljoin

# Suppress warnings for self-signed certs (optional, for testing)
requests.packages.urllib3.disable_warnings()


def test_endpoint(name, method, path, expected_status=200, expect_json=False, headers=None):
    """Test a single endpoint.
    
    Args:
        name: Test name for display
        method: HTTP method (GET, POST, etc.)
        path: URL path relative to base
        expected_status: Expected HTTP status code(s)
        expect_json: If True, verify response is valid JSON
        headers: Optional headers dict
    
    Returns:
        (passed, message) tuple
    """
    base_url = os.getenv('NUTRITRACK_URL')
    if not base_url:
        return False, 'NUTRITRACK_URL not set'
    
    url = urljoin(base_url, path)
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10, verify=False)
        elif method == 'POST':
            response = requests.post(url, headers=headers, timeout=10, verify=False)
        else:
            return False, f'Unsupported method: {method}'
        
        # Check status code
        if isinstance(expected_status, (list, tuple)):
            if response.status_code not in expected_status:
                return False, f'Status {response.status_code}, expected {expected_status}'
        else:
            if response.status_code != expected_status:
                return False, f'Status {response.status_code}, expected {expected_status}'
        
        # Check JSON if requested
        if expect_json:
            try:
                response.json()
            except json.JSONDecodeError:
                return False, 'Response is not valid JSON'
        
        return True, f'Status {response.status_code}'
    
    except requests.exceptions.Timeout:
        return False, 'Request timeout (10s)'
    except requests.exceptions.ConnectionError as e:
        return False, f'Connection failed: {e}'
    except Exception as e:
        return False, f'Error: {e}'


def main():
    """Run all smoke tests."""
    base_url = os.getenv('NUTRITRACK_URL')
    
    if not base_url:
        print('ERROR: NUTRITRACK_URL environment variable is required')
        print('Example: NUTRITRACK_URL=https://nutritrack-abc123.run.app')
        sys.exit(1)
    
    print('NutriTrack Smoke Tests')
    print('=' * 70)
    print(f'Target URL: {base_url}')
    print('=' * 70)
    print()
    
    tests = [
        ('Health check', 'GET', '/health', 200, True),
        ('Login page', 'GET', '/login', 200, False),
        ('Register page', 'GET', '/register', 200, False),
        ('Home page (redirect if AUTH_ENABLED)', 'GET', '/', [200, 302], False),
        ('API: Foods (auth required)', 'GET', '/api/foods', 401, True),
        ('API: Chat status', 'GET', '/api/chat/status', [200, 401], False),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, method, path, expected_status, expect_json in tests:
        success, message = test_endpoint(
            test_name, method, path, expected_status, expect_json
        )
        
        status = 'PASS' if success else 'FAIL'
        print(f'[{status}] {test_name:40} {message}')
        
        if success:
            passed += 1
        else:
            failed += 1
    
    print()
    print('=' * 70)
    print(f'Results: {passed} passed, {failed} failed')
    print('=' * 70)
    
    if failed > 0:
        sys.exit(1)
    else:
        print('All tests passed!')
        sys.exit(0)


if __name__ == '__main__':
    main()