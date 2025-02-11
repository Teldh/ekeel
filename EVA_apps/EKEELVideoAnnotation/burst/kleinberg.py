import math
import numpy as np

"""
Copyright:
https://pypi.org/project/pybursts/

Taken from github repository of pyburst and added minor fixes to adapted it for Python3.
Note for Python2 users only, add: from __future__ import division)

"""


def kleinberg(offsets: list, s: float, gamma: float) -> np.array:
    """
    KLEINBERG'S BURSTS ANALYSIS ALGORITHM

    It detects the intervals of a bursting activity of a word in a text,
    given the indexes of the sentences where the word appears.

    Parameters
    ----------
    offsets : list
        A list of indexes of the sentences where the word appears (must be non-empty).
    s : float
        The base of the exponential distribution (must be greater than 1).
    gamma : float
        The coefficient of the costs between states (must be positive).

    Returns
    -------
    np.array
        A numpy array containing all the intervals of burst.

    Raises
    ------
    ValueError
        If s <= 1.
    ValueError
        If gamma <= 0.
    ValueError
        If offsets is empty.
    ValueError
        If input contains events with zero time between.
    """

    if s <= 1:
        raise ValueError("S must be greater than 1!")
    if gamma <= 0:
        raise ValueError("Gamma must be positive!")
    if len(offsets) < 1:
        raise ValueError("offsets must be non-empty!")

    offsets = np.array(offsets, dtype=object)

    if offsets.size == 1:
        bursts = np.array([0, offsets[0], offsets[0]], ndmin=2, dtype=object)
        return bursts

    offsets = np.sort(offsets)
    gaps = np.diff(offsets)

    if not np.all(gaps):
        raise ValueError("Input cannot contain events with zero time between!")

    T = np.sum(gaps)
    n = np.size(gaps)
    g_hat = T / n

    k = int(math.ceil(float(1 + math.log(T, s) + math.log(1 / np.amin(gaps), s))))

    gamma_log_n = gamma * math.log(n)

    def tau(i, j):
        if i >= j:
            return 0
        else:
            return (j - i) * gamma_log_n

    alpha_function = np.vectorize(lambda x: s ** x / g_hat)
    alpha = alpha_function(np.arange(k))

    def f(j, x):
        return alpha[j] * math.exp(-alpha[j] * x)

    C = np.repeat(float("inf"), k)
    C[0] = 0

    q = np.empty((k, 0))
    for t in range(n):
        C_prime = np.repeat(float("inf"), k)
        q_prime = np.empty((k, t + 1))
        q_prime.fill(np.nan)

        for j in range(k):
            cost_function = np.vectorize(lambda x: C[x] + tau(x, j))
            cost = cost_function(np.arange(0, k))

            el = np.argmin(cost)

            if f(j, gaps[t]) > 0:
                C_prime[j] = cost[el] - math.log(f(j, gaps[t]))

            if t > 0:
                q_prime[j, :t] = q[el, :]

            q_prime[j, t] = j + 1

        C = C_prime
        q = q_prime

    j = np.argmin(C)
    q = q[j, :]

    prev_q = 0

    N = 0
    for t in range(n):
        if q[t] > prev_q:
            N = N + q[t] - prev_q
        prev_q = q[t]

    bursts = np.array([np.repeat(np.nan, N),
                       np.repeat(offsets[0], N),
                       np.repeat(offsets[0], N)],
                      ndmin=2, dtype=object).transpose()

    burst_counter = -1
    prev_q = 0
    stack = np.repeat(np.nan, N)
    stack_counter = -1
    for t in range(n):
        if q[t] > prev_q:
            num_levels_opened = q[t] - prev_q
            for i in range(int(num_levels_opened)):
                burst_counter += 1
                bursts[burst_counter, 0] = int(prev_q + i)
                bursts[burst_counter, 1] = offsets[t]
                stack_counter += 1
                stack[stack_counter] = burst_counter
        elif q[t] < prev_q:
            num_levels_closed = prev_q - q[t]
            for i in range(int(num_levels_closed)):
                bursts[int(stack[stack_counter]), 2] = offsets[t]  # fixed
                stack_counter -= 1
        prev_q = q[t]

    while stack_counter >= 0:
        bursts[int(stack[stack_counter]), 2] = offsets[n]  # fixed
        stack_counter -= 1

    return bursts
