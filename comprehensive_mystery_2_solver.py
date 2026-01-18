#!/usr/bin/env python3
"""
Comprehensive Mystery Function 2 Solver
Systematically test all hypotheses to identify the correct one.
"""

# Import the mystery function and hypotheses
import sys
sys.path.append('/Users/moskov/Code/benchmarks')
from mystery_function_2 import mystery_function
from mystery_function_2_hypothesis_tester import hypothesis_functions

def create_comprehensive_test_cases():
    """Create a comprehensive set of test cases to distinguish between hypotheses"""

    test_cases = [
        # Critical boundary cases for sum > 5
        (2, 3),    # sum = 5, should be False (not greater than 5)
        (3, 2),    # sum = 5, should be False
        (0, 5),    # sum = 5, should be False
        (1, 4),    # sum = 5, should be False
        (-1, 6),   # sum = 5, should be False

        # Cases where sum > 5
        (2, 4),    # sum = 6, should be True
        (3, 3),    # sum = 6, should be True
        (1, 5),    # sum = 6, should be True
        (0, 6),    # sum = 6, should be True
        (-1, 7),   # sum = 6, should be True
        (4, 3),    # sum = 7, should be True
        (10, 0),   # sum = 10, should be True

        # Cases where sum < 5
        (1, 2),    # sum = 3, should be False
        (0, 4),    # sum = 4, should be False
        (2, 2),    # sum = 4, should be False
        (-1, 5),   # sum = 4, should be False
        (0, 0),    # sum = 0, should be False
        (-2, 3),   # sum = 1, should be False

        # Edge cases with negatives
        (-5, 10),  # sum = 5, should be False
        (-3, 9),   # sum = 6, should be True
        (-10, 20), # sum = 10, should be True

        # Special cases for other hypotheses
        (1, 1),    # equal numbers (K)
        (5, 1),    # first > second (L)
        (1, 5),    # second > first (G)
        (8, 2),    # large difference (D)
        (9, 3),    # perfect powers (A)
        (2, 8),    # a^b > 30? (B)
        (4, 2),    # opposite parity (F)
        (6, 3),    # product % 3 == 1? (H)
        (3, 6),    # equal mod 3 (J)
        (7, 1),    # differ by at most 3? (N)
    ]

    return test_cases

def test_mystery_function_against_all_hypotheses():
    """Test the mystery function against all hypotheses"""

    print("MYSTERY FUNCTION 2 - COMPREHENSIVE HYPOTHESIS TESTING")
    print("=" * 70)

    # Get test cases
    test_cases = create_comprehensive_test_cases()

    print(f"\nTesting with {len(test_cases)} carefully chosen test cases...")
    print("Testing each case against the mystery function:")
    print()

    # Get actual results from mystery function
    actual_results = []
    for a, b in test_cases:
        result = mystery_function(a, b)
        actual_results.append(result)
        print(f"mystery_function({a:3}, {b:3}) = {str(result):5} (sum = {a + b:3})")

    print("\n" + "=" * 70)
    print("HYPOTHESIS TESTING RESULTS")
    print("=" * 70)

    # Test each hypothesis
    hypothesis_matches = {}

    for letter in sorted(hypothesis_functions.keys()):
        func = hypothesis_functions[letter]
        predicted_results = []

        for a, b in test_cases:
            try:
                predicted = func(a, b)
                predicted_results.append(predicted)
            except Exception as e:
                print(f"Error testing hypothesis {letter} with ({a}, {b}): {e}")
                predicted_results.append(None)

        # Count matches
        matches = 0
        for i in range(len(test_cases)):
            if predicted_results[i] == actual_results[i]:
                matches += 1

        match_percentage = (matches / len(test_cases)) * 100
        hypothesis_matches[letter] = (matches, match_percentage)

        print(f"Hypothesis {letter}: {matches:2}/{len(test_cases)} matches ({match_percentage:5.1f}%)")

        # Show first few mismatches if any
        if matches < len(test_cases):
            mismatches = []
            for i in range(len(test_cases)):
                if predicted_results[i] != actual_results[i]:
                    a, b = test_cases[i]
                    mismatches.append(f"({a},{b}): expected {actual_results[i]}, got {predicted_results[i]}")

            if mismatches:
                print(f"    First few mismatches: {', '.join(mismatches[:3])}")

        if matches == len(test_cases):
            print(f"    >>> PERFECT MATCH! Hypothesis {letter} matches ALL test cases! <<<")

    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)

    # Find the best hypothesis
    best_hypothesis = max(hypothesis_matches.keys(),
                         key=lambda k: hypothesis_matches[k][0])
    best_matches, best_percentage = hypothesis_matches[best_hypothesis]

    print(f"\nBest matching hypothesis: {best_hypothesis} with {best_matches}/{len(test_cases)} matches ({best_percentage:.1f}%)")

    # Show hypothesis description
    hypothesis_descriptions = {
        'A': "One argument is a perfect power of the other",
        'B': "First argument raised to power of second is greater than 30",
        'C': "Sum of arguments is greater than 5",
        'D': "Arguments differ by at least 5",
        'E': "Sum of arguments is a Fibonacci number",
        'F': "Arguments have opposite parity",
        'G': "Second argument is greater than first",
        'H': "Product of arguments is congruent to 1 modulo 3",
        'I': "Sum of arguments is a perfect square",
        'J': "Arguments are equal modulo 3",
        'K': "Both arguments are the same",
        'L': "First argument is greater than second",
        'M': "Sum of arguments is a triangular number",
        'N': "Arguments differ by at most 3",
        'O': "Sum of digits of product is a prime number"
    }

    if best_percentage == 100.0:
        print(f"\nCONCLUSION: The mystery function implements Hypothesis {best_hypothesis}")
        print(f"Description: {hypothesis_descriptions[best_hypothesis]}")
        print(f"\nMathematical expression: mystery_function(a, b) = {get_hypothesis_expression(best_hypothesis)}")
    else:
        print(f"\nNo hypothesis achieved 100% match. Best was {best_hypothesis} with {best_percentage:.1f}%")
        print("This suggests either:")
        print("1. Need more test cases to distinguish hypotheses")
        print("2. The mystery function implements a hypothesis not in our list")
        print("3. There's an error in our hypothesis implementations")

def get_hypothesis_expression(letter):
    """Get the mathematical expression for a hypothesis"""
    expressions = {
        'A': "is_perfect_power(a, b) or is_perfect_power(b, a)",
        'B': "a^b > 30",
        'C': "(a + b) > 5",
        'D': "abs(a - b) >= 5",
        'E': "is_fibonacci(a + b)",
        'F': "(a % 2) != (b % 2)",
        'G': "b > a",
        'H': "(a * b) % 3 == 1",
        'I': "is_perfect_square(a + b)",
        'J': "a % 3 == b % 3",
        'K': "a == b",
        'L': "a > b",
        'M': "is_triangular(a + b)",
        'N': "abs(a - b) <= 3",
        'O': "is_prime(sum_digits(a * b))"
    }
    return expressions.get(letter, "Unknown")

if __name__ == "__main__":
    test_mystery_function_against_all_hypotheses()