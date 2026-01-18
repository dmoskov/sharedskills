#!/usr/bin/env python3
"""
Systematic Hypothesis Testing for Mystery Function 0
This script will test the mystery function with various inputs and compare outputs
to determine which hypothesis is correct through pure input/output analysis.
"""

import sys
import os
sys.path.append('/Users/moskov/Code/benchmarks')

from mystery_function_0 import mystery_function, get_hypothesis_descriptions

def test_hypothesis_a(x):
    """Test hypothesis A: f(x) = x^2"""
    return x * x

def test_hypothesis_b(x):
    """Test hypothesis B: f(x) = 2*x"""
    return 2 * x

def test_hypothesis_c(x):
    """Test hypothesis C: f(x) = x + 3"""
    return x + 3

def test_hypothesis_d(x):
    """Test hypothesis D: f(x) = abs(x)"""
    return abs(x)

def test_hypothesis_e(x):
    """Test hypothesis E: f(x) = x^3"""
    return x * x * x

def systematic_test():
    """Systematically test the mystery function with various inputs."""

    print("MYSTERY FUNCTION 0 - HYPOTHESIS ELIMINATION")
    print("=" * 60)

    # Get hypothesis descriptions
    hypotheses = get_hypothesis_descriptions()
    print("Testing hypotheses:")
    for key, desc in hypotheses.items():
        print(f"  {key}: {desc}")
    print()

    # Test functions for each hypothesis
    hypothesis_functions = {
        'A': test_hypothesis_a,
        'B': test_hypothesis_b,
        'C': test_hypothesis_c,
        'D': test_hypothesis_d,
        'E': test_hypothesis_e
    }

    # Strategic test inputs to differentiate between hypotheses
    test_inputs = [
        0,    # Zero test - helps distinguish many functions
        1,    # Basic positive test
        -1,   # Negative test - helps distinguish abs() from others
        2,    # Small positive integer
        -2,   # Small negative integer
        3,    # Another positive for pattern recognition
        0.5,  # Decimal test
        -0.5, # Negative decimal
        4,    # Larger number to see if it's quadratic vs linear
        -3    # Another negative for comprehensive testing
    ]

    print("TESTING RESULTS:")
    print("-" * 60)
    print(f"{'Input':<8} {'Mystery':<10} {'A(x²)':<8} {'B(2x)':<8} {'C(x+3)':<8} {'D(|x|)':<8} {'E(x³)':<8}")
    print("-" * 60)

    # Track which hypotheses are still viable
    viable_hypotheses = set(['A', 'B', 'C', 'D', 'E'])

    for x in test_inputs:
        mystery_result = mystery_function(x)

        hypothesis_results = {}
        for hyp_key, hyp_func in hypothesis_functions.items():
            hypothesis_results[hyp_key] = hyp_func(x)

        # Print results
        print(f"{x:<8} {mystery_result:<10} ", end="")
        for hyp_key in ['A', 'B', 'C', 'D', 'E']:
            result = hypothesis_results[hyp_key]
            print(f"{result:<8} ", end="")
        print()

        # Eliminate hypotheses that don't match
        eliminated_this_round = []
        for hyp_key in list(viable_hypotheses):
            if hypothesis_results[hyp_key] != mystery_result:
                viable_hypotheses.remove(hyp_key)
                eliminated_this_round.append(hyp_key)

        if eliminated_this_round:
            print(f"    → Eliminated: {', '.join(eliminated_this_round)}")

    print("-" * 60)
    print(f"\nRESULT ANALYSIS:")
    print(f"Viable hypotheses remaining: {list(viable_hypotheses)}")

    if len(viable_hypotheses) == 1:
        winner = list(viable_hypotheses)[0]
        print(f"\n✅ CONCLUSION: The mystery function implements Hypothesis {winner}")
        print(f"    {hypotheses[winner]}")
    elif len(viable_hypotheses) == 0:
        print("\n❌ ERROR: No hypotheses match all test results!")
    else:
        print(f"\n⚠️  Multiple hypotheses still viable: {list(viable_hypotheses)}")
        print("Need additional discriminating tests.")

    return viable_hypotheses

def additional_verification():
    """Run additional tests to verify the conclusion."""
    print("\n" + "=" * 60)
    print("ADDITIONAL VERIFICATION")
    print("=" * 60)

    # Test with more challenging inputs if hypothesis A (x²) is suspected
    verification_inputs = [5, -5, 10, -10, 100, 0.1, -0.1]

    print("Verifying with additional test cases:")
    print(f"{'Input':<8} {'Mystery':<10} {'Expected x²':<12} {'Match':<8}")
    print("-" * 40)

    all_match = True
    for x in verification_inputs:
        mystery_result = mystery_function(x)
        expected_square = x * x
        matches = mystery_result == expected_square

        print(f"{x:<8} {mystery_result:<10} {expected_square:<12} {'✓' if matches else '✗':<8}")

        if not matches:
            all_match = False

    print("-" * 40)
    if all_match:
        print("✅ All verification tests confirm: f(x) = x² (Hypothesis A)")
    else:
        print("❌ Verification tests failed!")

if __name__ == "__main__":
    viable = systematic_test()
    if 'A' in viable:
        additional_verification()