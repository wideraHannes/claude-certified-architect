def calculate_average(numbers):
    """Return the arithmetic mean of ``numbers``, or 0 if the sequence is empty.

    Args:
        numbers: An iterable of numeric values to average.

    Returns:
        The mean as a float, or 0 when ``numbers`` is empty.
    """
    if not numbers:
        return 0
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)


def fibonacci(n):
    """Return the ``n``-th Fibonacci number using an iterative approach.

    The sequence is zero-indexed: ``fibonacci(0) == 0`` and
    ``fibonacci(1) == 1``.

    Args:
        n: A non-negative integer index into the Fibonacci sequence.

    Returns:
        The ``n``-th Fibonacci number as an ``int``.

    Raises:
        TypeError: If ``n`` is not an integer (``bool`` is rejected).
        ValueError: If ``n`` is negative.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")

    previous, current = 0, 1
    for _ in range(n):
        previous, current = current, previous + current
    return previous


def get_user_name(user):
    """Return the user's name in uppercase, or an empty string if unavailable.

    Args:
        user: A mapping expected to contain a ``"name"`` key.

    Returns:
        The uppercased name as a string, or ``""`` when ``user`` is falsy or
        has no ``"name"`` key.
    """
    if not user or "name" not in user:
        return ""
    return str(user["name"]).upper()
