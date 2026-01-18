#!/usr/bin/env python3
"""
Systematic hypothesis testing for mystery function 2
"""
import sys
sys.path.append('/Users/moskov/Code/benchmarks')

from mystery_function_2 import mystery_function
from mystery_function_2_hypothesis_tester import hypothesis_functions

def main():
    print("MYSTERY FUNCTION 2 - SYSTEMATIC HYPOTHESIS TESTING")
    print("=" * 60)

    # Comprehensive test cases to distinguish between hypotheses
    test_cases = [
        # From the examples we saw
        (1, 2),    # sum = 3
        (2, 4),    # sum = 6
        (3, 3),    # sum = 6
        (0, 6),    # sum = 6
        (1, 5),    # sum = 6
        (2, 3),    # sum = 5 (edge case for sum > 5)
        (-1, 7),   # sum = 6

        # Additional strategic test cases
        (0, 0),    # sum = 0
        (1, 1),    # sum = 2, equal numbers
        (5, 1),    # sum = 6, first > second
        (1, 4),    # sum = 5, edge case
        (3, 2),    # sum = 5, edge case
        (4, 2),    # sum = 6, powers
        (9, 3),    # 9 = 3^2, sum = 12
        (8, 2),    # 8 = 2^3, sum = 10
        (-2, 3),   # sum = 1, negative
        (10, 1),   # sum = 11, large difference
        (2, 8),    # sum = 10, large difference
        (-5, -2),  # sum = -7, both negative
        (0, 5),    # sum = 5, edge case with zero
        (6, 0),    # sum = 6, edge case with zero
    ]

    print(f"Testing {len(test_cases)} cases...")
    print("\nActual mystery function results:")

    actual_results = []
    for a, b in test_cases:
        result = mystery_function(a, b)
        actual_results.append(result)
        print(f"  mystery_function({a}, {b}) = {result}")

    print("\n" + "=" * 60)
    print("COMPARING AGAINST ALL HYPOTHESES:")
    print("=" * 60)

    # Test each hypothesis
    perfect_matches = []

    for letter in sorted(hypothesis_functions.keys()):
        func = hypothesis_functions[letter]
        hypothesis_results = []

        # Get results for this hypothesis
        for a, b in test_cases:
            try:
                result = func(a, b)
                hypothesis_results.append(result)
            except Exception as e:
                print(f"Error in hypothesis {letter} for ({a}, {b}): {e}")
                hypothesis_results.append(None)

        # Compare with actual results
        matches = 0
        total = 0
        for i in range(len(test_cases)):
            if hypothesis_results[i] is not None and actual_results[i] is not None:
                total += 1
                if hypothesis_results[i] == actual_results[i]:
                    matches += 1

        match_percent = (matches / total) * 100 if total > 0 else 0

        print(f"\nHypothesis {letter}: {matches}/{total} matches ({match_percent:.1f}%)")

        if matches == total and total > 0:
            perfect_matches.append(letter)
            print(f"  >>> PERFECT MATCH! <<<")

        # Show a few example comparisons for context
        print("  Sample comparisons:")
        for i in range(min(5, len(test_cases))):
            a, b = test_cases[i]
            actual = actual_results[i]
            hypothesis = hypothesis_results[i] if i < len(hypothesis_results) else None
            match_status = "✓" if hypothesis == actual else "✗"
            print(f"    f({a}, {b}): actual={actual}, hypothesis={hypothesis} {match_status}")

    print("\n" + "=" * 60)
    print("CONCLUSION:")
    print("=" * 60)

    if perfect_matches:
        print(f"Perfect matches found: {', '.join(perfect_matches)}")
        for letter in perfect_matches:
            # Get description from the hypothesis tester file
            if letter == 'A':
                desc = "one of the arguments is a perfect power of the other"
            elif letter == 'B':
                desc = "first argument raised to the power of the second is greater than 30"
            elif letter == 'C':
                desc = "sum of the arguments is greater than 5"
            elif letter == 'D':
                desc = "two arguments differ by at least 5"
            elif letter == 'E':
                desc = "sum of the arguments is a Fibonacci number"
            elif letter == 'F':
                desc = "two arguments have opposite parity"
            elif letter == 'G':
                desc = "second argument is greater than the first one"
            elif letter == 'H':
                desc = "product of the arguments is congruent to 1 modulo 3"
            elif letter == 'I':
                desc = "sum of the arguments is a perfect square"
            elif letter == 'J':
                desc = "two arguments are equal modulo 3"
            elif letter == 'K':
                desc = "both arguments are the same"
            elif letter == 'L':
                desc = "first argument is greater than the second one"
            elif letter == 'M':
                desc = "sum of the arguments is a triangular number"
            elif letter == 'N':
                desc = "two arguments differ by at most 3"
            elif letter == 'O':
                desc = "sum of the digits of the product of the numbers is a prime number"
            else:
                desc = "unknown"

            print(f"Hypothesis {letter}: The function returns True if and only if the {desc}")
    else:
        print("No perfect matches found! This suggests:")
        print("1. Need more test cases to distinguish hypotheses")
        print("2. There might be an error in the hypothesis implementations")
        print("3. The mystery function implements a different pattern")

if __name__ == "__main__":
    main()