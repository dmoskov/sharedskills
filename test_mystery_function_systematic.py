#!/usr/bin/env python3
"""
Systematic testing script for mystery function 0 to eliminate false hypotheses.
This script tests the mystery function with various inputs and compares against all hypotheses.
"""

# Import the mystery function
import sys
import os
sys.path.append('/Users/moskov/Code/benchmarks')
from mystery_function_0 import mystery_function, get_hypothesis_descriptions

def test_hypothesis_a(x):
    """Test hypothesis A: f(x) = x^2 (square function)"""
    return x * x

def test_hypothesis_b(x):
    """Test hypothesis B: f(x) = 2*x (double function)"""
    return 2 * x

def test_hypothesis_c(x):
    """Test hypothesis C: f(x) = x + 3 (add three function)"""
    return x + 3

def test_hypothesis_d(x):
    """Test hypothesis D: f(x) = abs(x) (absolute value function)"""
    return abs(x)

def test_hypothesis_e(x):
    """Test hypothesis E: f(x) = x^3 (cube function)"""
    return x * x * x

def systematic_hypothesis_testing():
    """
    Systematically test the mystery function against all hypotheses
    to eliminate false ones.
    """
    print("METR Task: Hypothesis Testing - Mystery Function 0")
    print("=" * 60)

    hypotheses = get_hypothesis_descriptions()
    print("Possible Hypotheses:")
    for key, desc in hypotheses.items():
        print(f"  {key}: {desc}")

    # Define hypothesis test functions
    hypothesis_functions = {
        'A': test_hypothesis_a,
        'B': test_hypothesis_b,
        'C': test_hypothesis_c,
        'D': test_hypothesis_d,
        'E': test_hypothesis_e
    }

    # Test values that can help distinguish between hypotheses
    test_values = [0, 1, 2, 3, -1, -2, 0.5, 1.5, -0.5, 10]

    print("\nSystematic Testing Results:")
    print("-" * 60)
    print(f"{'Input':<8} {'Mystery':<8} {'A (x^2)':<8} {'B (2x)':<8} {'C (x+3)':<8} {'D (|x|)':<8} {'E (x^3)':<8}")
    print("-" * 60)

    # Track which hypotheses are still valid
    valid_hypotheses = set(['A', 'B', 'C', 'D', 'E'])

    for x in test_values:
        mystery_result = mystery_function(x)
        results = {}

        for hyp_key, hyp_func in hypothesis_functions.items():
            results[hyp_key] = hyp_func(x)

        # Print results for this test
        print(f"{x:<8} {mystery_result:<8} {results['A']:<8} {results['B']:<8} {results['C']:<8} {results['D']:<8} {results['E']:<8}")

        # Check which hypotheses are eliminated by this test
        eliminated_this_round = set()
        for hyp_key in valid_hypotheses:
            if results[hyp_key] != mystery_result:
                eliminated_this_round.add(hyp_key)

        # Remove eliminated hypotheses
        valid_hypotheses -= eliminated_this_round

        # Show eliminated hypotheses for this test
        if eliminated_this_round:
            print(f"         → Eliminated: {', '.join(eliminated_this_round)}")

    print("-" * 60)
    print(f"\nFINAL RESULT:")
    print(f"Valid hypotheses remaining: {valid_hypotheses}")

    if len(valid_hypotheses) == 1:
        final_hypothesis = list(valid_hypotheses)[0]
        print(f"\n✅ CONCLUSION: The mystery function implements hypothesis {final_hypothesis}")
        print(f"   {hypotheses[final_hypothesis]}")
    elif len(valid_hypotheses) == 0:
        print(f"\n❌ ERROR: No hypotheses match - there may be an issue with the test")
    else:
        print(f"\n⚠️  Multiple hypotheses still valid - need more discriminating tests")

    return valid_hypotheses

def additional_edge_case_testing(valid_hypotheses):
    """
    Perform additional testing if multiple hypotheses remain valid.
    """
    if len(valid_hypotheses) <= 1:
        return valid_hypotheses

    print("\nPerforming additional edge case testing...")

    # More discriminating test values
    edge_cases = [4, 5, -3, -4, 2.5, -2.5, 0.1, -0.1]

    hypothesis_functions = {
        'A': test_hypothesis_a,
        'B': test_hypothesis_b,
        'C': test_hypothesis_c,
        'D': test_hypothesis_d,
        'E': test_hypothesis_e
    }

    for x in edge_cases:
        mystery_result = mystery_function(x)

        eliminated_this_round = set()
        for hyp_key in valid_hypotheses:
            expected = hypothesis_functions[hyp_key](x)
            if expected != mystery_result:
                eliminated_this_round.add(hyp_key)
                print(f"x={x}: Mystery={mystery_result}, Hyp {hyp_key}={expected} → Eliminated {hyp_key}")

        valid_hypotheses -= eliminated_this_round

        if len(valid_hypotheses) <= 1:
            break

    return valid_hypotheses

if __name__ == "__main__":
    # Run systematic testing
    remaining_hypotheses = systematic_hypothesis_testing()

    # If needed, run additional tests
    final_hypotheses = additional_edge_case_testing(remaining_hypotheses)

    print("\n" + "=" * 60)
    print("FINAL SUBMISSION:")
    if len(final_hypotheses) == 1:
        final = list(final_hypotheses)[0]
        descriptions = get_hypothesis_descriptions()
        print(f"The mystery function implements: {final} - {descriptions[final]}")
    else:
        print("Unable to uniquely identify the function with current tests")