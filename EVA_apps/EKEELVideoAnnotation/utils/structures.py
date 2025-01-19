class Node:
    """
    A node class for implementing linked data structures.

    Attributes
    ----------
    value : any
        The value stored in the node.
    _prev : Node or None
        Reference to the previous node in the structure.

    Methods
    -------
    set_prev(prev)
        Sets the previous node reference and returns self.
    get_prev()
        Returns the previous node reference.
    """
    def __init__(self,value=None):
        self.value = value
        self._prev:Node or None = None
    
    def set_prev(self,prev) -> 'Node':
        self._prev = prev 
        return self
    
    def get_prev(self) -> 'Node or None':
        return self._prev


class LiFoStack:
    """
    Last-In-First-Out (LIFO) stack implementation using linked nodes.

    A stack data structure that follows the LIFO principle where elements
    are added and removed from the same end.

    Attributes
    ----------
    _tail : Node
        The tail node of the stack.
    _cursor : Node
        Current position for iteration.
    _len : int
        Number of elements in the stack.

    Methods
    -------
    push(elem)
        Pushes an element onto the top of the stack.
    get(indx=None, raise_exception=False)
        Returns but does not remove the top element.
    pop(raise_exception=False)
        Removes and returns the top element.
    is_head(self)
        Checks if the stack is at the head position.
    """
    _tail = Node()
    _cursor = _tail
    _len = 0

    def __init__(self,from_list:'list'= None) -> None:
        if from_list is not None: i=0; [ self.push(elem) for elem in from_list ]

    def __str__(self):
        cur = self._tail.get_prev()
        out = ""
        max_len = 0
        # can be improved but for now is just for debug purposes
        while cur is not None:
            max_len = max(max_len, len(str(cur.value)))
            out += "| " + str(cur.value) + " |\n"
            cur = cur.get_prev()
        if out=="":
            out= "empty"
        return out + "⎿"+"⎽"*max_len+"⎽⎽⎽⎽"+"⏌ "

    def __iter__(self):
        return self

    def __next__(self):
        node = self._cursor.get_prev()
        if node is not None:
            self._cursor = node
            return node.value
        else:
            self._cursor = self._tail
            raise StopIteration()
    
    def __len__(self):
        return self._len
    
    def is_head(self):
        return self._tail.get_prev() is None

    def push(self,elem):
        """
        Pushes an element onto the top of the stack.

        Parameters
        ----------
        elem : any
            The element to be pushed onto the stack.
        """
        curr_tail = self._tail
        curr_tail.value = elem
        self._tail = Node().set_prev(curr_tail)
        self._cursor = self._tail
        self._len += 1

    def get(self,indx=None,raise_exception=False):
        """
        Returns but does not remove the top element of the stack.

        Parameters
        ----------
        indx : int, optional
            Currently unused parameter.
        raise_exception : bool, default=False
            If True, raises an exception when stack is empty.

        Returns
        -------
        any or None
            The top element of the stack, or None if stack is empty
            and raise_exception is False.

        Raises
        ------
        Exception
            If the stack is empty and raise_exception is True.
        """
        tail = self._tail
        if tail.get_prev() is None:
            if raise_exception:
                raise Exception("Popping from an empty stack")
            else:
                return None
        return tail.get_prev().value

    def pop(self,raise_exception=False):
        """
        Removes and returns the top element of the stack.

        Parameters
        ----------
        raise_exception : bool, default=False
            If True, raises an exception when stack is empty.

        Returns
        -------
        any or None
            The top element of the stack, or None if stack is empty
            and raise_exception is False.
        """
        value = self.get(raise_exception)
        if value is not None:
            self._tail = self._tail.get_prev()
            self._len -= 1
        return value