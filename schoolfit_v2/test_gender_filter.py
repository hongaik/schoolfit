#!/usr/bin/env python3
"""Quick test to verify gender filter logic."""

# Test the gender filter logic
test_cases = [
    ("M", "M", True),     # Boy, boys school → pass
    ("M", "F", False),    # Boy, girls school → fail
    ("M", "MF", True),    # Boy, co-ed → pass
    ("F", "F", True),     # Girl, girls school → pass
    ("F", "M", False),    # Girl, boys school → fail
    ("F", "MF", True),    # Girl, co-ed → pass
]

print("Testing gender filter logic: return True if gender in nature_code else None")
for gender, nature_code, expected_pass in test_cases:
    result = gender in nature_code
    status = "✓" if result == expected_pass else "✗ BUG"
    print(f"  {status} gender={gender}, nature_code={nature_code}: '{gender}' in '{nature_code}' = {result} (expected {expected_pass})")
