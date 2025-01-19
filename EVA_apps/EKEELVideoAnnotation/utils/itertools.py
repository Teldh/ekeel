from itertools import zip_longest, tee
from typing import Generator, Iterable

def _pairwise_linked_reversed(iterable, None_tail):
    """
    Internal function that returns reversed pairs from an iterable.

    Parameters
    ----------
    iterable : Iterable
        The input iterable to process
    None_tail : bool
        Whether to append None as the last pair element

    Returns
    -------
    Generator
        Yields pairs of elements in reverse order
    """
    curr_index = len(iterable)-1
    while curr_index > 0:
        yield iterable[curr_index], iterable[curr_index-1]
        curr_index -= 1
    if None_tail:
        yield iterable[0], None
    return

def pairwise(iterable, None_tail=True, reversed=False) -> Generator:
    """
    Generator of linked element pairs from an iterable.

    Creates pairs of successive elements from the input iterable,
    optionally including None as the final pair element.

    Parameters
    ----------
    iterable : Iterable
        The input iterable to process
    None_tail : bool, default=True
        If True, includes (last_element, None) as final pair
    reversed : bool, default=False
        If True, yields pairs in reverse order

    Returns
    -------
    Generator
        Yields tuples of paired elements
    """
    if not reversed:
        a,b = tee(iterable)
        next(b,None)
        return zip_longest(a,b, fillvalue=None) if None_tail else zip(a,b)
    else: return _pairwise_linked_reversed(iterable,None_tail)


def pairwise_iterator(iterable, None_tail=True, reversed=False) -> 'Generator[Iterable, Iterable or None]':
    """
    Generator that yields non-overlapping pairs from an iterable.

    Unlike pairwise(), this generates distinct pairs without overlap
    between successive pairs.

    Parameters
    ----------
    iterable : Iterable
        The input iterable to process
    None_tail : bool, default=True
        If True, yields (last_element, None) for odd-length iterables
    reversed : bool, default=False
        If True, yields pairs in reverse order

    Returns
    -------
    Generator
        Yields tuples of paired elements
    """
    if not reversed:
        iterable = iter(iterable)
        while True:
            try: a = next(iterable)
            except StopIteration: return

            try: yield a,next(iterable)
            except StopIteration: 
                if None_tail: 
                    yield a, None 
                return
    else:
        curr_index = len(iterable)-1
        while curr_index > 1:
            yield iterable[curr_index], iterable[curr_index-1]
            curr_index -= 2
        if None_tail and curr_index == 0:
            yield iterable[0], None
        return

def double_iterator(iterable, enumerated:bool=False) -> 'Generator[Iterable,Iterable] or Generator[int,int,Iterable,Iterable]':
    """
    Generates all possible pairs of elements from an iterable.

    Creates pairs representing both upper and lower triangular matrix elements,
    excluding diagonal (self-pairs).

    Parameters
    ----------
    iterable : Iterable
        The input iterable to process
    enumerated : bool, default=False
        If True, yields (index1, index2, value1, value2) instead of (value1, value2)

    Returns
    -------
    Generator
        If enumerated=False: yields (value1, value2) tuples
        If enumerated=True: yields (index1, index2, value1, value2) tuples

    Examples
    --------
    >>> list(double_iterator([1,2,3]))
    [(1,2), (1,3), (2,1), (2,3), (3,1), (3,2)]
    """
    if not enumerated:
        for x in iter(iterable):
            for y in iter(iterable):
                if x is not y:
                    yield (x,y)
    else:
        for i, x in enumerate(iter(iterable)):
            for j, y in enumerate(iter(iterable)):
                if x is not y:
                    yield (i, j, x, y)
