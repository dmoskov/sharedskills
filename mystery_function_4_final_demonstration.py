#!/usr/bin/env python3
"""
Mystery Function 4 - Final Demonstration
Demonstrates the discovered pattern and validates the solution
"""

from mystery_function_4 import mystery_function_4

def demonstrate_solution():
    """Demonstrate the discovered pattern with clear examples"""

    print("MYSTERY FUNCTION 4 - SOLUTION DEMONSTRATION")
    print("=" * 55)
    print("DISCOVERED RULE: Returns True if sum(args) % 7 == 0")
    print("=" * 55)

    # Categories of test cases
    categories = [
        ("Multiples of 7 (should return True)", [
            [0],
            [7],
            [14],
            [21],
            [-7],
            [-14],
            [3, 4],      # 3 + 4 = 7
            [10, 11],    # 10 + 11 = 21
            [1, 1, 1, 1, 1, 1, 1],  # sum = 7
        ]),

        ("Non-multiples of 7 (should return False)", [
            [1],
            [6],
            [8],
            [15],
            [2, 2],      # 2 + 2 = 4
            [7, 8],      # 7 + 8 = 15
            [1, 2, 3, 4, 5],  # sum = 15
        ])
    ]

    total_tests = 0
    correct_predictions = 0

    for category_name, test_cases in categories:
        print(f"\n{category_name}:")
        print("-" * len(category_name))

        for args in test_cases:
            actual_result = mystery_function_4(args)
            sum_val = sum(args)
            expected_result = (sum_val % 7 == 0)
            is_correct = actual_result == expected_result

            status = "✓" if is_correct else "✗"
            print(f"{status} f({args}) = {actual_result} | sum = {sum_val:3d} | divisible by 7: {expected_result}")

            total_tests += 1
            if is_correct:
                correct_predictions += 1

    # Summary
    print(f"\n{'='*55}")
    print("SUMMARY")
    print("="*55)
    print(f"Total tests: {total_tests}")
    print(f"Correct predictions: {correct_predictions}")
    print(f"Accuracy: {correct_predictions/total_tests*100:.1f}%")

    if correct_predictions == total_tests:
        print("\n✅ SOLUTION CONFIRMED!")
        print("The mystery function returns True if and only if")
        print("the sum of its arguments is divisible by 7.")
    else:
        print("\n❌ Solution needs revision.")

def show_mathematical_proof():
    """Show mathematical examples of the divisibility rule"""

    print("\n" + "="*55)
    print("MATHEMATICAL VERIFICATION")
    print("="*55)
    print("Demonstrating modular arithmetic properties:")

    examples = [
        ("Zero is divisible by 7", [0], 0),
        ("7 ≡ 0 (mod 7)", [7], 7),
        ("14 = 2×7 ≡ 0 (mod 7)", [14], 14),
        ("-7 ≡ 0 (mod 7)", [-7], -7),
        ("3 + 4 = 7 ≡ 0 (mod 7)", [3, 4], 7),
        ("1×7 = 7 ≡ 0 (mod 7)", [1]*7, 7),
        ("10 + 11 = 21 = 3×7 ≡ 0 (mod 7)", [10, 11], 21),
        ("6 ≢ 0 (mod 7)", [6], 6),
        ("2 + 2 = 4 ≢ 0 (mod 7)", [2, 2], 4),
        ("15 = 2×7 + 1 ≢ 0 (mod 7)", [1, 2, 3, 4, 5], 15),
    ]

    for description, args, expected_sum in examples:
        actual_sum = sum(args)
        result = mystery_function_4(args)
        remainder = actual_sum % 7

        print(f"\n{description}")
        print(f"  Input: {args}")
        print(f"  Sum: {actual_sum}, Remainder when divided by 7: {remainder}")
        print(f"  Function result: {result}")

if __name__ == "__main__":
    demonstrate_solution()
    show_mathematical_proof()

    print(f"\n{'='*55}")
    print("FINAL ANSWER")
    print("="*55)
    print("mystery_function_4(args) returns True if and only if sum(args) % 7 == 0")
    print("In other words: the function checks if the sum of arguments is divisible by 7")