#!/usr/bin/env python3
"""
Test runner for Alan's AI Assistant
Runs all tests and provides comprehensive test results
"""

import unittest
import sys
import os
import tempfile
import shutil
from io import StringIO

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_all_tests():
    """Run all tests and return results"""
    print("🧪 Running Alan's AI Assistant Test Suite")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test modules
    test_modules = [
        'tests.test_email_modules',
        'tests.test_ai_modules', 
        'tests.test_rag_engine',
        'tests.test_integration',
        'tests.test_api_endpoints'
    ]
    
    # Load tests from each module
    for module_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            loader = unittest.TestLoader()
            tests = loader.loadTestsFromModule(module)
            test_suite.addTests(tests)
            print(f"✅ Loaded tests from {module_name}")
        except Exception as e:
            print(f"❌ Failed to load tests from {module_name}: {e}")
    
    # Run tests
    print(f"\n🚀 Running {test_suite.countTestCases()} tests...")
    print("-" * 50)
    
    # Capture output
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(test_suite)
    
    # Print results
    print(stream.getvalue())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = total_tests - failures - errors - skipped
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failures}")
    print(f"💥 Errors: {errors}")
    print(f"⏭️  Skipped: {skipped}")
    
    if failures > 0:
        print(f"\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if errors > 0:
        print(f"\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # Overall result
    if failures == 0 and errors == 0:
        print(f"\n🎉 ALL TESTS PASSED! Alan's AI Assistant is working correctly!")
        return True
    else:
        print(f"\n⚠️  Some tests failed. Please check the errors above.")
        return False

def run_specific_test_module(module_name):
    """Run tests from a specific module"""
    print(f"🧪 Running tests from {module_name}")
    print("=" * 50)
    
    try:
        module = __import__(module_name, fromlist=[''])
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    except Exception as e:
        print(f"❌ Failed to run tests from {module_name}: {e}")
        return False

def run_quick_smoke_test():
    """Run a quick smoke test to verify basic functionality"""
    print("🔥 Running Quick Smoke Test")
    print("=" * 30)
    
    try:
        # Test basic imports
        from email_modules.parser import EmailParser
        from ai_modules.conversation_memory import ConversationMemory
        from rag_engine import RAGEngine
        
        print("✅ Basic imports successful")
        
        # Test basic initialization
        parser = EmailParser()
        print("✅ Email parser initialized")
        
        # Test with temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_file.close()
        
        try:
            memory = ConversationMemory(memory_file=temp_file.name)
            print("✅ Conversation memory initialized")
        finally:
            os.unlink(temp_file.name)
        
        # Test RAG engine with mocked OpenAI
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('rag_engine.OpenAI') as mock_openai:
                mock_client = Mock()
                mock_openai.return_value = mock_client
                mock_client.embeddings.create.return_value = Mock(
                    data=[Mock(embedding=[0.1] * 1536)]
                )
                
                rag_engine = RAGEngine()
                print("✅ RAG engine initialized")
        
        print("\n🎉 Smoke test passed! Basic functionality is working.")
        return True
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import argparse
    from unittest.mock import patch, Mock
    
    parser = argparse.ArgumentParser(description='Run Alan\'s AI Assistant tests')
    parser.add_argument('--module', help='Run tests from specific module')
    parser.add_argument('--smoke', action='store_true', help='Run quick smoke test')
    
    args = parser.parse_args()
    
    if args.smoke:
        success = run_quick_smoke_test()
    elif args.module:
        success = run_specific_test_module(args.module)
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)
