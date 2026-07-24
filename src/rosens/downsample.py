def decimate[T](sequence: list[T], max_points: int) -> list[T]:
    """Thin a time-ordered sequence to roughly ``max_points`` via every-Nth decimation.

    Returns ``sequence`` unchanged when it already fits (so short periods are untouched)
    or when ``max_points`` is not positive. Otherwise keeps every ``step``-th element and
    always appends the final element, so the line still reaches the end of the period.
    The result therefore holds at most ``max_points + 1`` elements.
    """
    n = len(sequence)
    if max_points <= 0 or n <= max_points:
        return sequence
    step = (n + max_points - 1) // max_points  # ceil(n / max_points)
    thinned = sequence[::step]
    if thinned[-1] is not sequence[-1]:
        thinned.append(sequence[-1])
    return thinned
