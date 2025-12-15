"""
Master test runner for all task-related tests.
Runs CRUD, assignee status, and integration tests.
"""
import subprocess
import sys
import os

def run_tests():
    """Run all task-related test suites."""
    test_files = [
        'test_task_crud.py',
        'test_assignee_status.py',
    ]
    
    print("=" * 80)
    print("RUNNING COMPREHENSIVE TASK MANAGEMENT TESTS")
    print("=" * 80)
    print()
    
    all_passed = True
    
    for test_file in test_files:
        print(f"\n{'='*80}")
        print(f"Running: {test_file}")
        print(f"{'='*80}\n")
        
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short'],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode != 0:
            all_passed = False
            print(f"\n❌ {test_file} FAILED")
        else:
            print(f"\n✅ {test_file} PASSED")
    
    print(f"\n{'='*80}")
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print(f"{'='*80}\n")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(run_tests())
