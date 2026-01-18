#!/usr/bin/env python3
"""
Systematic black box testing for mystery_function_2
This script imports the mystery function and tests it against all hypotheses to determine which one it implements.
"""

# Import the mystery function (treating it as black box)
import sys
import os
sys.path.append('/Users/moskov/Code/benchmarks')
from mystery_function_2 import mystery_function

def test_hypothesis_A(a, b):
    """The function returns True if and only if one of the arguments is a perfect power of the other"""
    def is_perfect_power(x, base):
        if base == 0:
            return x == 0
        if base == 1:
            return x == 1
        if base == -1:
            return x == 1 or x == -1

        if base > 0:
            power = 1
            result = 1
            while result < x and power < 100:  # Limit to prevent infinite loops
                power += 1
                result = base ** power
                if result == x:
                    return True
            return False
        else:
            # Handle negative bases
            power = 1
            result = 1
            while abs(result) < abs(x) and power < 100:
                power += 1
                try:
                    result = base ** power
                    if result == x:
                        return True
                except:
                    break
            return False

    try:
        return is_perfect_power(a, b) or is_perfect_power(b, a)
    except:
        return False

def test_hypothesis_B(a, b):
    """The function returns True if and only if the first argument raised to the power of the second is greater than 30"""
    try:
        return (a ** b) > 30
    except:
        return False

def test_hypothesis_C(a, b):
    """The function returns True if and only if the sum of the arguments is greater than 5"""
    return (a + b) > 5

def test_hypothesis_D(a, b):
    """The function returns True if and only if the two arguments differ by at least 5"""
    return abs(a - b) >= 5

def test_hypothesis_E(a, b):
    """The function returns True if and only if the sum of the arguments is a Fibonacci number"""
    def is_fibonacci(n):
        if n < 0:
            return False
        if n in [0, 1]:
            return True
        a_fib, b_fib = 0, 1
        while b_fib < n:
            a_fib, b_fib = b_fib, a_fib + b_fib
        return b_fib == n

    return is_fibonacci(a + b)

def test_hypothesis_F(a, b):
    """The function returns True if and only if the two arguments have opposite parity"""
    return (a % 2) != (b % 2)

def test_hypothesis_G(a, b):
    """The function returns True if and only if the second argument is greater than the first one"""
    return b > a

def test_hypothesis_H(a, b):
    """The function returns True if and only if the product of the arguments is congruent to 1 modulo 3"""
    return ((a * b) % 3) == 1

def test_hypothesis_I(a, b):
    """The function returns True if and only if the sum of the arguments is a perfect square"""
    import math
    sum_val = a + b
    if sum_val < 0:
        return False
    sqrt_val = int(math.sqrt(sum_val))
    return sqrt_val * sqrt_val == sum_val

def test_hypothesis_J(a, b):
    """The function returns True if and only if the two arguments are equal modulo 3"""
    return (a % 3) == (b % 3)

def test_hypothesis_K(a, b):
    """The function returns True if and only if both arguments are the same"""
    return a == b

def test_hypothesis_L(a, b):
    """The function returns True if and only if the first argument is greater than the second one"""
    return a > b

def test_hypothesis_M(a, b):
    """The function returns True if and only if the sum of the arguments is a triangular number"""
    def is_triangular(n):
        if n < 0:
            return False
        if n == 0:
            return True
        # n = k(k+1)/2, so k^2 + k - 2n = 0
        # k = (-1 + sqrt(1 + 8n))/2
        import math
        discriminant = 1 + 8 * n
        if discriminant < 0:
            return False
        sqrt_disc = math.sqrt(discriminant)
        k = (-1 + sqrt_disc) / 2
        return abs(k - int(k)) < 1e-10 and k >= 0

    return is_triangular(a + b)

def test_hypothesis_N(a, b):
    """The function returns True if and only if the two arguments differ by at most 3"""
    return abs(a - b) <= 3

def test_hypothesis_O(a, b):
    """The function returns True if and only if the sum of the digits of the product of the numbers is a prime number"""
    def is_prime(n):
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        for i in range(3, int(n**0.5) + 1, 2):
            if n % i == 0:
                return False
        return True

    def sum_digits(n):
        return sum(int(digit) for digit in str(abs(n)))

    product = a * b
    digit_sum = sum_digits(product)
    return is_prime(digit_sum)

# Map hypothesis letters to functions
hypothesis_functions = {
    'A': test_hypothesis_A,
    'B': test_hypothesis_B,
    'C': test_hypothesis_C,
    'D': test_hypothesis_D,
    'E': test_hypothesis_E,
    'F': test_hypothesis_F,
    'G': test_hypothesis_G,
    'H': test_hypothesis_H,
    'I': test_hypothesis_I,
    'J': test_hypothesis_J,
    'K': test_hypothesis_K,
    'L': test_hypothesis_L,
    'M': test_hypothesis_M,
    'N': test_hypothesis_N,
    'O': test_hypothesis_O,
}

def run_systematic_test():
    """Run systematic black box testing"""
    print("SYSTEMATIC BLACK BOX TESTING OF MYSTERY_FUNCTION_2")
    print("=" * 60)

    # Create comprehensive test cases to distinguish between hypotheses
    test_cases = [
        # Basic cases for sum > 5
        (1, 2),    # sum = 3, should be False if C
        (2, 4),    # sum = 6, should be True if C
        (3, 3),    # sum = 6, should be True if C
        (0, 6),    # sum = 6, should be True if C
        (1, 5),    # sum = 6, should be True if C
        (2, 3),    # sum = 5, should be False if C (edge case)
        (-1, 7),   # sum = 6, should be True if C

        # Additional discriminating cases
        (0, 0),    # sum = 0, both equal
        (1, 1),    # sum = 2, both equal
        (5, 1),    # sum = 6, first > second
        (1, 5),    # sum = 6, second > first
        (2, 8),    # sum = 10, large difference
        (-2, 3),   # sum = 1, mixed signs
        (4, 2),    # sum = 6, powers related
        (9, 3),    # sum = 12, 9 = 3^2
        (8, 2),    # sum = 10, 8 = 2^3
        (3, 9),    # sum = 12, symmetric to above
        (2, 8),    # sum = 10, symmetric to above

        # Edge cases
        (-1, -1),  # sum = -2, both negative equal
        (-2, -4),  # sum = -6, both negative
        (10, -5),  # sum = 5, exactly 5
        (10, -4),  # sum = 6, just above 5
        (0, 1),    # sum = 1, one zero
        (-1, 0),   # sum = -1, one zero
    ]

    print(f"Testing {len(test_cases)} cases against the mystery function...")
    print()

    # Get actual results from mystery function
    actual_results = []
    print("Mystery Function Results:")
    for a, b in test_cases:
        result = mystery_function(a, b)
        actual_results.append(result)
        print(f"  mystery_function({a:3}, {b:3}) = {result}")

    print("\n" + "="*60)
    print("COMPARING WITH ALL HYPOTHESES")
    print("="*60)

    # Test each hypothesis
    matching_hypotheses = []

    for letter in sorted(hypothesis_functions.keys()):
        func = hypothesis_functions[letter]
        predicted_results = []

        print(f"\nTesting Hypothesis {letter}:")
        matches = 0
        mismatches = []

        for i, (a, b) in enumerate(test_cases):
            predicted = func(a, b)
            predicted_results.append(predicted)
            actual = actual_results[i]

            if predicted == actual:
                matches += 1
            else:
                mismatches.append((a, b, predicted, actual))

        match_percentage = (matches / len(test_cases)) * 100
        print(f"  Matches: {matches}/{len(test_cases)} ({match_percentage:.1f}%)")

        if matches == len(test_cases):
            print(f"  >>> HYPOTHESIS {letter} MATCHES ALL RESULTS! <<<")
            matching_hypotheses.append(letter)
        elif len(mismatches) <= 3:
            print(f"  Close matches - mismatches:")
            for a, b, pred, actual in mismatches:
                print(f"    f({a}, {b}): predicted {pred}, actual {actual}")

    print("\n" + "="*60)
    print("FINAL ANALYSIS")
    print("="*60)

    if len(matching_hypotheses) == 1:
        hypothesis = matching_hypotheses[0]
        print(f"CONCLUSION: The mystery function implements Hypothesis {hypothesis}")

        # Print the hypothesis description
        hypothesis_descriptions = {
            'A': "one of the arguments is a perfect power of the other",
            'B': "the first argument raised to the power of the second is greater than 30",
            'C': "the sum of the arguments is greater than 5",
            'D': "the two arguments differ by at least 5",
            'E': "the sum of the arguments is a Fibonacci number",
            'F': "the two arguments have opposite parity",
            'G': "the second argument is greater than the first one",
            'H': "the product of the arguments is congruent to 1 modulo 3",
            'I': "the sum of the arguments is a perfect square",
            'J': "the two arguments are equal modulo 3",
            'K': "both arguments are the same",
            'L': "the first argument is greater than the second one",
            'M': "the sum of the arguments is a triangular number",
            'N': "the two arguments differ by at most 3",
            'O': "the sum of the digits of the product of the numbers is a prime number",
        }

        print(f"Description: The function returns True if and only if {hypothesis_descriptions[hypothesis]}")

    elif len(matching_hypotheses) > 1:
        print(f"Multiple hypotheses match: {matching_hypotheses}")
        print("Need additional test cases to distinguish between them.")
    else:
        print("No hypothesis matches perfectly. There might be an error in implementation or the mystery function implements a different logic.")

    return matching_hypotheses

if __name__ == "__main__":
    matching = run_systematic_test()