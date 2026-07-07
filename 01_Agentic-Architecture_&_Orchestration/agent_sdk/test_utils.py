import unittest

from utils import fibonacci


class FibonacciTests(unittest.TestCase):
    def test_base_cases(self):
        self.assertEqual(fibonacci(0), 0)
        self.assertEqual(fibonacci(1), 1)

    def test_small_values(self):
        self.assertEqual(fibonacci(2), 1)
        self.assertEqual(fibonacci(3), 2)
        self.assertEqual(fibonacci(10), 55)

    def test_sequence(self):
        expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
        self.assertEqual([fibonacci(n) for n in range(11)], expected)

    def test_larger_value(self):
        self.assertEqual(fibonacci(30), 832040)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            fibonacci(-1)

    def test_non_integer_raises(self):
        with self.assertRaises(TypeError):
            fibonacci(2.5)

    def test_bool_rejected(self):
        with self.assertRaises(TypeError):
            fibonacci(True)


if __name__ == "__main__":
    unittest.main()
