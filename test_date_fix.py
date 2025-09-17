#!/usr/bin/env python3
"""
Test script to verify date validation fix
"""

import sys
import os
from datetime import datetime, date

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validation import validate_dates

def test_date_validation():
    """Test date validation with different date types"""
    print("🧪 Testing Date Validation Fix")
    print("=" * 40)
    
    # Test cases
    test_cases = [
        {
            'name': 'datetime objects',
            'start': datetime(2024, 1, 1),
            'end': datetime(2024, 1, 31),
            'should_pass': True
        },
        {
            'name': 'date objects',
            'start': date(2024, 1, 1),
            'end': date(2024, 1, 31),
            'should_pass': True
        },
        {
            'name': 'mixed date/datetime',
            'start': date(2024, 1, 1),
            'end': datetime(2024, 1, 31),
            'should_pass': True
        },
        {
            'name': 'invalid range (start > end)',
            'start': datetime(2024, 1, 31),
            'end': datetime(2024, 1, 1),
            'should_pass': False
        },
        {
            'name': 'too far in future',
            'start': datetime(2025, 1, 1),
            'end': datetime(2026, 1, 1),
            'should_pass': False
        },
        {
            'name': 'too old',
            'start': datetime(2019, 1, 1),
            'end': datetime(2019, 1, 31),
            'should_pass': False
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing {test_case['name']}:")
        print(f"   Start: {test_case['start']}")
        print(f"   End: {test_case['end']}")
        
        is_valid, error_msg = validate_dates(test_case['start'], test_case['end'])
        
        if is_valid == test_case['should_pass']:
            print(f"   ✅ PASS - {'Valid' if is_valid else 'Invalid'}")
        else:
            print(f"   ❌ FAIL - Expected {test_case['should_pass']}, got {is_valid}")
            if not is_valid:
                print(f"   Error: {error_msg}")
    
    print(f"\n🎉 Date validation test completed!")

if __name__ == "__main__":
    test_date_validation()
