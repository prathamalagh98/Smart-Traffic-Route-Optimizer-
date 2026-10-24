"""Sorting algorithms (Syllabus Unit-1, Experiment 1).

Every function returns ``(sorted_list, comparisons)`` so that the empirical
analysis can count basic operations as well as measure wall-clock time.
An optional ``key`` function allows sorting objects (used to rank routes).
"""
import random


def _decorate(data, key):
    """Attach (key, index) so ties never compare the payload and sorts are stable."""
    return [(key(x), i, x) for i, x in enumerate(data)]


def _undecorate(items):
    return [t[2] for t in items]


def bubble_sort(data, key=None):
    """Bubble sort with early exit.  Best O(n) | Average/Worst O(n^2)."""
    if key:
        out, c = bubble_sort(_decorate(data, key))
        return _undecorate(out), c
    a = list(data)
    n = len(a)
    comps = 0
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            comps += 1
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:          # already sorted -> best case Omega(n)
            break
    return a, comps


def merge_sort(data, key=None):
    """Top-down merge sort.  T(n) = 2T(n/2) + n  =>  Theta(n log n) in all cases."""
    if key:
        out, c = merge_sort(_decorate(data, key))
        return _undecorate(out), c
    counter = [0]

    def sort(a):
        if len(a) <= 1:
            return a
        mid = len(a) // 2
        left, right = sort(a[:mid]), sort(a[mid:])
        merged, i, j = [], 0, 0
        while i < len(left) and j < len(right):
            counter[0] += 1
            if left[i] <= right[j]:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
        merged.extend(left[i:])
        merged.extend(right[j:])
        return merged

    return sort(list(data)), counter[0]


def quick_sort(data, key=None, pivot="random"):
    """Iterative quick sort (Lomuto partition).

    pivot="random" : expected Theta(n log n) on every input
    pivot="last"   : classic textbook version, worst case Theta(n^2) on sorted input
    The explicit stack always processes the smaller part first, so the stack
    stays O(log n) deep and Python's recursion limit is never hit.
    """
    if key:
        out, c = quick_sort(_decorate(data, key), pivot=pivot)
        return _undecorate(out), c
    a = list(data)
    comps = 0
    rng = random.Random(12345)
    stack = [(0, len(a) - 1)]
    while stack:
        lo, hi = stack.pop()
        if lo >= hi:
            continue
        if pivot == "random":
            p = rng.randint(lo, hi)
            a[p], a[hi] = a[hi], a[p]
        pv = a[hi]
        i = lo
        for j in range(lo, hi):
            comps += 1
            if a[j] < pv:
                a[i], a[j] = a[j], a[i]
                i += 1
        a[i], a[hi] = a[hi], a[i]
        left, right = (lo, i - 1), (i + 1, hi)
        if (left[1] - left[0]) > (right[1] - right[0]):
            stack.append(left)
            stack.append(right)
        else:
            stack.append(right)
            stack.append(left)
    return a, comps
