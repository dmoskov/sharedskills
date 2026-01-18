#!/usr/bin/env python3
"""
Mystery Function 4 Analysis - Black Box Testing
Testing various inputs to determine the function's behavior pattern
"""

# Import the mystery function
from mystery_function_4 import mystery_function_4

def run_comprehensive_tests():
    """Run comprehensive tests to understand the function behavior"""

    print("Mystery Function 4 - Comprehensive Analysis")
    print("=" * 50)

    # Test 1: Basic single values
    print("\n1. Testing single values (0-20):")
    single_values = list(range(21))
    for val in single_values:
        result = mystery_function_4([val])
        print(f"f([{val}]) = {result}")

    # Test 2: Test with pairs that sum to specific values
    print("\n2. Testing pairs with various sums:")
    pairs = [
        [0, 0],     # sum = 0
        [1, 0],     # sum = 1
        [1, 1],     # sum = 2
        [1, 2],     # sum = 3
        [2, 2],     # sum = 4
        [2, 3],     # sum = 5
        [3, 3],     # sum = 6
        [3, 4],     # sum = 7
        [4, 4],     # sum = 8
        [4, 5],     # sum = 9
        [5, 5],     # sum = 10
        [5, 6],     # sum = 11
        [6, 6],     # sum = 12
        [6, 7],     # sum = 13
        [7, 7],     # sum = 14
        [7, 8],     # sum = 15
        [10, 4],    # sum = 14
        [10, 11],   # sum = 21
    ]

    for pair in pairs:
        result = mystery_function_4(pair)
        sum_val = sum(pair)
        print(f"f({pair}) = {result} (sum = {sum_val})")

    # Test 3: Negative values
    print("\n3. Testing negative values:")
    negative_tests = [
        [-1],
        [-7],
        [-14],
        [-21],
        [7, -7],    # sum = 0
        [10, -3],   # sum = 7
        [-3, -4],   # sum = -7
        [-10, -11], # sum = -21
    ]

    for test in negative_tests:
        result = mystery_function_4(test)
        sum_val = sum(test)
        print(f"f({test}) = {result} (sum = {sum_val})")

    # Test 4: Longer lists
    print("\n4. Testing longer lists:")
    long_lists = [
        [1, 1, 1, 1, 1, 1, 1],      # sum = 7
        [1, 1, 1, 1, 1, 1, 1, 1],   # sum = 8
        [2, 2, 2, 1],               # sum = 7
        [3, 3, 3, 3, 2],           # sum = 14
        [1, 2, 3, 4, 5],           # sum = 15
        [1, 2, 3, 4, 5, 6],        # sum = 21
        [0, 0, 0, 0, 0, 7],        # sum = 7
    ]

    for test in long_lists:
        result = mystery_function_4(test)
        sum_val = sum(test)
        print(f"f({test}) = {result} (sum = {sum_val})")

def analyze_patterns():
    """Analyze the patterns from test results"""
    print("\n" + "=" * 50)
    print("PATTERN ANALYSIS")
    print("=" * 50)

    # Group results by sum value
    test_cases = []

    # Collect various test cases
    for i in range(25):
        test_cases.append(([i], i))

    # Additional test cases
    additional_tests = [
        ([3, 4], 7),
        ([10, 11], 21),
        ([5, 2], 7),
        ([1, 1, 1, 1, 1, 1, 1], 7),
        ([2, 2, 2, 1], 7),
        ([7, 7], 14),
        ([-7], -7),
        ([-14], -14),
        ([7, -7], 0),
        ([10, -3], 7),
    ]
    test_cases.extend(additional_tests)

    # Group by sum and analyze
    results_by_sum = {}
    for args, expected_sum in test_cases:
        actual_sum = sum(args)
        result = mystery_function_4(args)
        if actual_sum not in results_by_sum:
            results_by_sum[actual_sum] = []
        results_by_sum[actual_sum].append((args, result))

    print("\nResults grouped by sum:")
    for sum_val in sorted(results_by_sum.keys()):
        results = results_by_sum[sum_val]
        all_results = [r[1] for r in results]
        print(f"Sum {sum_val:3d}: {all_results[0]} (consistent: {len(set(all_results)) == 1})")
        for args, result in results[:3]:  # Show first 3 examples
            print(f"    f({args}) = {result}")

def test_hypothesis():
    """Test the hypothesis that the function returns True if sum % 7 == 0"""
    print("\n" + "=" * 50)
    print("HYPOTHESIS TESTING: Returns True if sum divisible by 7")
    print("=" * 50)

    # Test specific cases for this hypothesis
    test_cases = [
        # Multiples of 7 (should be True)
        [0],
        [7],
        [14],
        [21],
        [28],
        [-7],
        [-14],
        [-21],
        [3, 4],      # sum = 7
        [10, 11],    # sum = 21
        [2, 5],      # sum = 7
        [1, 6],      # sum = 7

        # Non-multiples of 7 (should be False)
        [1],
        [2],
        [8],
        [15],
        [22],
        [1, 1],      # sum = 2
        [4, 4],      # sum = 8
        [7, 8],      # sum = 15
    ]

    correct_predictions = 0
    total_tests = len(test_cases)

    print("\nTesting hypothesis:")
    for args in test_cases:
        actual_result = mystery_function_4(args)
        sum_val = sum(args)
        predicted_result = (sum_val % 7 == 0)
        is_correct = actual_result == predicted_result
        correct_predictions += is_correct

        status = "✓" if is_correct else "✗"
        print(f"{status} f({args}) = {actual_result}, sum = {sum_val}, predicted = {predicted_result}")

    accuracy = correct_predictions / total_tests * 100
    print(f"\nHypothesis accuracy: {correct_predictions}/{total_tests} ({accuracy:.1f}%)")

    return accuracy == 100.0

if __name__ == "__main__":
    # Run comprehensive tests
    run_comprehensive_tests()

    # Analyze patterns
    analyze_patterns()

    # Test hypothesis
    hypothesis_confirmed = test_hypothesis()

    print("\n" + "=" * 50)
    print("CONCLUSION")
    print("=" * 50)
    if hypothesis_confirmed:
        print("✓ HYPOTHESIS CONFIRMED!")
        print("The mystery function returns True if and only if the sum of arguments is divisible by 7.")
        print("Mathematical formula: mystery_function_4(args) = (sum(args) % 7 == 0)")
    else:
        print("✗ Hypothesis not confirmed. Need further investigation.")