"""An object-oriented interface to Prolog."""
from collections import namedtuple
from ctypes import (
    POINTER,
    byref,
    c_char,
    c_double,
    c_int,
    c_int64,
    c_size_t,
    c_void_p,
)

from swilite.core import (
    BUF_DISCARDABLE,
    CVT_WRITEQ,
    PL_ATOM,
    PL_BLOB,
    PL_DICT,
    PL_FLOAT,
    PL_INTEGER,
    PL_LIST_PAIR,
    PL_NIL,
    PL_Q_CATCH_EXCEPTION,
    PL_Q_NODEBUG,
    PL_STRING,
    PL_TERM,
    PL_VARIABLE,
    PL_atom_chars,
    PL_call,
    PL_call_predicate,
    PL_chars_to_term,
    PL_close_foreign_frame,
    PL_close_query,
    PL_cons_functor,
    PL_cons_functor_v,
    PL_cons_list,
    PL_context,
    PL_copy_term_ref,
    PL_discard_foreign_frame,
    PL_erase,
    PL_exception,
    PL_functor_arity,
    PL_functor_name,
    PL_get_arg,
    PL_get_atom,
    PL_get_atom_nchars,
    PL_get_bool,
    PL_get_compound_name_arity,
    PL_get_float,
    PL_get_functor,
    PL_get_head,
    PL_get_int64,
    PL_get_list,
    PL_get_module,
    PL_get_name_arity,
    PL_get_nchars,
    PL_get_nil,
    PL_get_pointer,
    PL_get_string_chars,
    PL_get_tail,
    PL_is_acyclic,
    PL_is_atom,
    PL_is_atomic,
    PL_is_callable,
    PL_is_compound,
    PL_is_float,
    PL_is_functor,
    PL_is_ground,
    PL_is_integer,
    PL_is_list,
    PL_is_number,
    PL_is_pair,
    PL_is_string,
    PL_is_variable,
    PL_module_name,
    PL_new_atom,
    PL_new_functor,
    PL_new_module,
    PL_new_term_ref,
    PL_new_term_refs,
    PL_next_solution,
    PL_open_foreign_frame,
    PL_open_query,
    PL_pred,
    PL_predicate,
    PL_predicate_info,
    PL_put_atom,
    PL_put_atom_nchars,
    PL_put_bool,
    PL_put_float,
    PL_put_functor,
    PL_put_int64,
    PL_put_list,
    PL_put_list_nchars,
    PL_put_nil,
    PL_put_pointer,
    PL_put_string_nchars,
    PL_put_term,
    PL_put_variable,
    PL_record,
    PL_recorded,
    PL_register_atom,
    PL_rewind_foreign_frame,
    PL_term_type,
    PL_unify,
    PL_unify_arg,
    PL_unify_atom,
    PL_unify_atom_nchars,
    PL_unify_bool,
    PL_unify_compound,
    PL_unify_float,
    PL_unify_functor,
    PL_unify_int64,
    PL_unify_list,
    PL_unify_list_nchars,
    PL_unify_nil,
    PL_unify_pointer,
    PL_unify_string_nchars,
    PL_unregister_atom,
    REP_UTF8,
    atom_t,
    functor_t,
    module_t,
    state as prolog_state,
)

_term_type_code_name = {
    PL_VARIABLE: 'variable',
    PL_ATOM: 'atom',
    PL_INTEGER: 'integer',
    PL_FLOAT: 'float',
    PL_STRING: 'string',
    PL_TERM: 'compound',
    PL_NIL: 'nil',
    PL_BLOB: 'blob',
    PL_LIST_PAIR: 'list-pair',
    PL_DICT: 'dict',
}

__all__ = [
    'Atom',
    'Frame',
    'Functor',
    'Module',
    'Predicate',
    'PrologCallFailed',
    'PrologException',
    'PrologMemoryError',
    'Query',
    'Term',
    'TermList',
    'TermRecord',
]


class PrologException(Exception):
    """An exception raised within the Prolog system."""
    def __init__(self, exception_term):
        super().__init__()
        self.exception_term = exception_term

    def __str__(self):
        return "Prolog Exception:\n{!s}".format(self.exception_term)

    def __repr__(self):
        return 'PrologException({!r})'.format(self.exception_term)


class PrologCallFailed(RuntimeError):
    """A call failed."""
    def __init__(self, msg):
        super().__init__()
        self.msg = msg

    def __str__(self):
        return str(self.msg)


class PrologMemoryError(Exception):
    """Prolog stack is out of memory."""
    pass


class HandleWrapper(object):
    """Class wrapping a handle."""
    def __init__(self, handle):
        self._handle = handle

    @classmethod
    def _from_handle(cls, handle):
        """Initialize from an existing handle."""
        if handle is None:
            # When the handle truly is 0, ctypes interprets the value as None.
            # Undo the mistake here.
            # Unfortunately, this means we can't warn about None being passed
            # when it's an error.
            handle = 0

        if not isinstance(handle, int):
            raise ValueError('Handle must be an int, not {}'.format(
                type(handle).__name__))
        new_obj = cls.__new__(cls)
        HandleWrapper.__init__(new_obj, handle=handle)
        return new_obj

    def __eq__(self, other):
        if type(other) is not type(self):
            return NotImplemented
        return self._handle == other._handle

    def __ne__(self, other):
        return not self == other


class TemporaryHandleMixIn(object):
    """Mixin for `HandleWrapper` where the handle can be invalidated."""
    _valid = True

    def __init__(self):
        super().__init__()

    def _get_handle(self):
        if self._valid:
            return self.__handle
        raise AttributeError('handle been invalidated')

    def _set_handle(self, handle):
        self.__handle = handle

    _handle = property(fget=_get_handle, fset=_set_handle)

    def _invalidate(self):
        """Invalidate the handle."""
        self._valid = False


class ConstantHandleToConstantMixIn(object):
    """`HandleWrapper` mixin where `_handle` is constant and refers to a
    constant object.

    """
    def __hash__(self):
        return hash(self._handle)


def _decode_ptr_len_string(ptr, length, encoding='utf8'):
    """Decode a string from a ctypes pointer and length."""
    return ptr[:length.value].decode(encoding)


class Atom(HandleWrapper):
    """Prolog Atom Interface"""
    def __init__(self, name):
        """Create a named atom."""
        super().__init__(handle=PL_new_atom(name.encode()))

    @classmethod
    def _from_handle(cls, handle):
        """Create an Atom object from an existing atom handle."""
        new_atom = super()._from_handle(handle)
        PL_register_atom(new_atom._handle)
        return new_atom

    def __str__(self):
        return self.get_name()

    def __repr__(self):
        return 'Atom(name={name!r})'.format(name=self.get_name())

    def __del__(self):
        if prolog_state.is_available:
            PL_unregister_atom(self._handle)

    def __copy__(self):
        """A new `Atom` object pointing to the same atom."""
        return self._from_handle(self._handle)

    def __eq__(self, other):
        if type(other) is not type(self):
            return NotImplemented
        # Atoms can have different handles but the same name.
        return self.get_name() == other.get_name()

    def __hash__(self):
        return hash(self.get_name())

    def get_name(self):
        """The atom's name as a string."""
        return PL_atom_chars(self._handle).decode()


class Functor(HandleWrapper, ConstantHandleToConstantMixIn):
    """Prolog Functor Interface"""
    def __init__(self, name, arity):
        """Create a functor.

        Args:
            name (Atom): Name of the functor.
                Either Atom object or string, the former is more efficient.
            arity (int): Arity of the functor.
        """
        try:
            name_handle = name._handle
        except AttributeError:
            name_handle = Atom(name=name)._handle

        super().__init__(handle=PL_new_functor(name_handle, arity))

    def __str__(self):
        return "{name}/{arity}".format(name=self.get_name(),
                                       arity=self.get_arity())

    def __repr__(self):
        return "Functor(name={name!r}, arity={arity!r})".format(
            name=self.get_name(), arity=self.get_arity())

    def __eq__(self, other):
        if type(other) is not type(self):
            return NotImplemented
        return (self.get_name() == other.get_name() and
                self.get_arity() == other.get_arity())

    def __hash__(self):
        return hash((self.get_name(), self.get_arity()))

    def __call__(self, *args):
        """Returns a new compound term created from this functor and `args`.

        The length of `args` must be the same as the arity of `functor`.
        See `Term.from_cons_functor`.
        """
        return Term.from_cons_functor(self, *args)

    def get_name(self):
        """The functor's name as an `Atom` object."""
        return Atom._from_handle(PL_functor_name(self._handle))

    def get_arity(self):
        """The functor's arity as an integer."""
        return PL_functor_arity(self._handle)


class Module(HandleWrapper, ConstantHandleToConstantMixIn):
    """Prolog Module Interface"""
    def __init__(self, name):
        """Finds existing module or creates a new module with given name.

        Args:
            name (Atom): Name of the module.
        """
        super().__init__(handle=PL_new_module(name._handle))

    def __str__(self):
        return str(self.get_name())

    def __repr__(self):
        return 'Module(name={name!r})'.format(name=self.get_name())

    def __eq__(self, other):
        if type(other) is not type(self):
            return NotImplemented
        return self.get_name() == other.get_name()

    def __hash__(self):
        return hash(self.get_name())

    @classmethod
    def current_context(cls):
        """Returns the current context module."""
        return cls._from_handle(PL_context())

    def get_name(self):
        """The name of the module as an `Atom` object."""
        return Atom._from_handle(PL_module_name(self._handle))


class Predicate(HandleWrapper, ConstantHandleToConstantMixIn):
    """Prolog Predicate Interface"""
    def __init__(self, functor, module=None):
        """Create a predicate from a functor.

        Args:
            functor (Functor): Functor used to create the predicate.
            module (Module)  : Module containing the functor.
                If ``None``, uses the current context module.
        """
        super().__init__(
            handle=PL_pred(functor._handle, _get_nullable_handle(module)))

    @classmethod
    def from_name_arity(cls, name, arity, module_name=None):
        """Create a predicate directly from Python's built-in types.

        Args:
            name (str)       : Name of functor used to create the predicate.
            arity (int)      : Arity of functor used to create the predicate.
            module_name (str): Name of module containing the functor.
                If ``None``, uses the current context module.
        """
        return cls._from_handle(handle=PL_predicate(
            name.encode(), arity,
            module_name.encode() if module_name is not None else None))

    def __str__(self):
        info = self.get_info()
        return '{module_prefix}{name}/{arity}'.format(
            module_prefix=(str(info.module) + ':'
                           if info.module is not None else ''),
            name=info.name,
            arity=info.arity)

    def __repr__(self):
        info = self.get_info()
        return 'Predicate(functor={functor!r}, module={module!r})'.format(
            functor=Functor(name=info.name, arity=info.arity),
            module=info.module)

    def __eq__(self, other):
            if type(other) is not type(self):
                return NotImplemented
            return self.get_info() == other.get_info()

    def __hash__(self):
        return hash(self.get_info())

    def __call__(self, *arguments, arglist=None, goal_context_module=None,
                 check=False):
        """Call predicate with arguments.

        Finds a binding for arguments that satisfies the predicate.
        Like Query but only finds the first solution.

        Args:
            *arguments (Term)           : Terms to pass as arguments to this
                predicate.
            arglist (TermList)          : Arguments to this predicate.
                Cannot pass both arguments and arglist.
            goal_context_module (Module): Context module of the goal.
                If ``None``, the current context module is used, or ``user`` if
                there is no context. This only matters for meta_predicates.
            check (bool)                : Check that the call succeeded.

        Returns:
            bool: True if a binding for `arguments` was found.

        Raises:
            PrologException : If an exception was raised in Prolog.
            PrologCallFailed: If the call failed and `check` is ``True``.
        """
        if arglist is None:
            arglist = TermList.from_terms(*arguments)
        elif arguments:
            raise ValueError('Cannot provide both "arguments" and "arglist".')
        self.check_argument_match(arglist)
        success = bool(PL_call_predicate(
            _get_nullable_handle(goal_context_module),
            PL_Q_NODEBUG | PL_Q_CATCH_EXCEPTION,
            self._handle,
            arglist._handle))

        if check and not success:
            raise PrologCallFailed(str(self))
        return success

    Info = namedtuple('Info', ['name', 'arity', 'module'])

    def get_info(self):
        """Returns name, arity, and module of this predicate.

        Returns:
            Predicate.Info:
        """
        name = atom_t()
        arity = c_int()
        module = module_t()
        PL_predicate_info(self._handle,
                          byref(name), byref(arity), byref(module))
        return self.Info(name=Atom._from_handle(name.value),
                         arity=arity.value,
                         module=Module._from_handle(module.value))

    def check_argument_match(self, arguments):
        """Check that the right number of arguments are given.

        Args:
            arguments (TermList): List of arguments.

        Raises:
            ValueError : If the number of arguments does not match
                the predicate's arity.
        """
        number_of_arguments = len(arguments)
        arity = self.get_info().arity
        if number_of_arguments != arity:
            raise ValueError(
                ('number of arguments ({nargs}) does not match '
                 'predicate arity ({arity})').format(
                     nargs=number_of_arguments,
                     arity=arity))


class Term(HandleWrapper):
    """Prolog Term Interface."""
    _equality_predicate = Predicate.from_name_arity(name='==', arity=2)
    _logical_or_functor = Functor(';', 2)
    _logical_and_functor = Functor(',', 2)

    def __init__(self):
        """Initialize a new term. The term is initially a variable."""
        super().__init__(handle=PL_new_term_ref())

    def __str__(self):
        """A Prolog string representing this term."""
        return self.get_chars()

    def __repr__(self):
        return ('Term(handle={handle!r}, type={type!r}, value={value!r})'
                .format(handle=self._handle, type=self.type(),
                        value=self.get_chars()))

    def __eq__(self, other):
        """Check if two terms have the same value. Does not perform unification.
        """
        try:
            return self._equality_predicate(self, other)
        except AttributeError as e:
            if '_handle' not in str(e):
                raise
            return NotImplemented

    def __or__(self, other):
        """Logical OR of two terms."""
        return self._logical_or_functor(self, other)

    def __and__(self, other):
        """Logical AND of two terms."""
        return self._logical_and_functor(self, other)

    def __int__(self):
        """Integer representation of this term (if it stores an integer)."""
        return self.get_integer()

    def __float__(self):
        """Float representation of this term (if it stores a float)."""
        return self.get_float()

    def __deepcopy__(self, memo):
        """Creates a new Prolog term, copied from the old."""
        return self.from_term(self)

    def type(self):
        """Term type as a string.

        Returns one of the following strings:

            * ``variable``
            * ``atom``
            * ``integer``
            * ``float``
            * ``string``
            * ``term``
            * ``nil``
            * ``blob``
            * ``list-pair``
            * ``dict``
        """
        type_code = PL_term_type(self._handle)
        return _term_type_code_name[type_code]

    def is_acyclic(self):
        """True if this is an acyclic term."""
        return bool(PL_is_acyclic(self._handle))

    def is_atom(self):
        """True if this term is an atom."""
        return bool(PL_is_atom(self._handle))

    def is_atomic(self):
        """True if this term is atomic.

        A term is atomic if it is not variable or compound.
        """
        return bool(PL_is_atomic(self._handle))

    def is_callable(self):
        """True if this term is callable.

        A term is callable if it is compound or an atom.
        """
        return bool(PL_is_callable(self._handle))

    def is_compound(self):
        """True if this term is compound.

        A compound term is a functor with arguments.
        """
        return bool(PL_is_compound(self._handle))

    def is_float(self):
        """True if this term is a float."""
        return bool(PL_is_float(self._handle))

    def is_functor(self, functor):
        """True if this term is compound and its functor is `functor`.

        Args:
            functor (Functor): Check if this is the functor of `self`.
        """
        return bool(PL_is_functor(self._handle, functor._handle))

    def is_ground(self):
        """True if this term is a ground term.

        A ground term is a term that holds no free variables.
        """
        return bool(PL_is_ground(self._handle))

    def is_integer(self):
        """True if this term is an integer."""
        return bool(PL_is_integer(self._handle))

    def is_list(self):
        """True if this term is a list.

        A term is a list if it is:
            * a compound term using the list constructor (`is_pair`); or
            * the list terminator (`is_nil`).

        Note:
            This definition is weaker than what is used by the prolog predicate
            ``is_list``, which has the additional constraint that the 2nd term
            in the list pair also be a list.

            For example,
            >>> Term.from_parsed('[1|2]').is_list()
            True
            >>> Term.from_parsed('is_list([1|2])')()
            False

        """
        return bool(PL_is_list(self._handle))

    def is_nil(self):
        """True if this term is the list terminator.

        The list terminator is the constant ``[]``.
        """
        return bool(PL_get_nil(self._handle))

    def is_number(self):
        """True if this term is an integer or float."""
        return bool(PL_is_number(self._handle))

    def is_pair(self):
        """True if this term is a compound term using the list constructor."""
        return bool(PL_is_pair(self._handle))

    def is_string(self):
        """True if this term is a string."""
        return bool(PL_is_string(self._handle))

    def is_variable(self):
        """True if this term is a variable."""
        return bool(PL_is_variable(self._handle))

    @staticmethod
    def _require_success(return_code):
        assert bool(return_code)

    @staticmethod
    def _require_success_expecting_type(return_code, *required_types):
        assert required_types
        if not bool(return_code):
            if len(required_types) == 1:
                type_str = required_types[0]
            elif len(required_types) == 2:
                type_str = '{} or {}'.format(*required_types)
            else:
                type_str = '{}, or {}'.format(
                    ', '.join(required_types[:-1],),
                    required_types[-1])

            raise TypeError('Term is not {a} {type}.'.format(
                a=('an' if type_str[0].lower() in 'aeiou' else 'a'),
                type=type_str))

    def get_atom(self):
        """An `Atom` object representing this term, if it is a prolog atom."""
        a = atom_t()
        self._require_success_expecting_type(
            PL_get_atom(self._handle, byref(a)),
            'atom')
        return Atom._from_handle(a.value)

    def get_atom_name(self):
        """The value of this term as a string, if it is a prolog atom."""
        s = POINTER(c_char)()
        length = c_size_t()
        self._require_success_expecting_type(
            PL_get_atom_nchars(self._handle, byref(length), byref(s)),
            'atom')
        return _decode_ptr_len_string(s, length)

    def get_string_chars(self):
        """The value of this term as a string, if it is a prolog string."""
        s = POINTER(c_char)()
        length = c_size_t()
        self._require_success_expecting_type(
            PL_get_string_chars(self._handle, byref(s), byref(length)),
            'string')
        return _decode_ptr_len_string(s, length)

    def get_chars(self):
        """Representation of this term as a string in Prolog syntax."""
        s = POINTER(c_char)()
        length = c_size_t()
        self._require_success(
            PL_get_nchars(self._handle,
                          byref(length),
                          byref(s),
                          CVT_WRITEQ | BUF_DISCARDABLE | REP_UTF8))
        return _decode_ptr_len_string(s, length, encoding='utf8')

    def get_integer(self):
        """The value of this term as an integer, if it is an integer or
        compatible float.
        """
        i = c_int64()
        self._require_success_expecting_type(
            PL_get_int64(self._handle, byref(i)),
            'integer', 'int-compatible float')
        return i.value

    def get_bool(self):
        """The value of this term as a boolean, if it is `true` or `false`."""
        i = c_int()
        self._require_success_expecting_type(
            PL_get_bool(self._handle, byref(i)),
            'boolean')
        return bool(i.value)

    def get_pointer(self):
        """The value of this term as an integer address, if it is a pointer."""
        p = c_void_p()
        self._require_success_expecting_type(
            PL_get_pointer(self._handle, byref(p)),
            'pointer')
        return p.value

    def get_float(self):
        """The value of this term as a float, if it is an integer or float."""
        f = c_double()
        self._require_success_expecting_type(
            PL_get_float(self._handle, byref(f)),
            'float', 'integer')
        return f.value

    def get_functor(self):
        """A `Functor` object representing this term, if it is a compound term
        or atom."""
        functor = functor_t()
        self._require_success_expecting_type(
            PL_get_functor(self._handle, byref(functor)),
            'compound term', 'atom')
        return Functor._from_handle(functor.value)

    NameArity = namedtuple('NameArity', ['name', 'arity'])

    def get_name_arity(self):
        """The name and arity of this term, if it is a compound term or an atom.

        Compound terms with arity 0 give the same result as an atom.
        To distinguish them use `is_compound` and/or `get_compound_name_arity`.

        Returns:
            NameArity: namedtuple (name, arity)
        """

        name = atom_t()
        arity = c_int()
        self._require_success_expecting_type(
            PL_get_name_arity(self._handle, byref(name), byref(arity)),
            'compound term', 'atom')
        return self.NameArity(name=Atom._from_handle(name.value),
                              arity=arity.value)

    def get_compound_name_arity(self):
        """The name and arity of this term, if it is a compound term.

        The same as `get_name_arity` but fails for atoms.

        Returns:
            NameArity: Named tuple of name (`string`) and arity (`int`).
        """
        name = atom_t()
        arity = c_int()
        self._require_success_expecting_type(
            PL_get_compound_name_arity(self._handle, byref(name),
                                       byref(arity)),
            'compound term')
        return self.NameArity(name=Atom._from_handle(name.value),
                              arity=arity.value)

    def get_module(self):
        """A `Module` object corresponding to this term, if it is an atom."""
        module = module_t()
        self._require_success_expecting_type(
            PL_get_module(self._handle, byref(module)),
            'atom')
        return Module._from_handle(module.value)

    def get_arg(self, index):
        """A new term with a reference to an argument of this term.

        Args:
            index (int): Index of the argument.
                Index is 0-based, unlike in Prolog.

        Returns:
            Term: A new term reference to the argument.

        Raises:
            AssertionError: If `index` is out of bounds or
                if this term is not compound.

        Note: This returns a _new_ term, not a the argument term itself.
            Therefore, using `put_*` methods on the return value will not
            change the argument itself, while unification will.
        """
        t = Term()
        self._require_success(
            PL_get_arg(index + 1, self._handle, t._handle))
        return t

    HeadTail = namedtuple('HeadTail', ['head', 'tail'])

    def get_list_head_tail(self):
        """Get the head and tail of the list represented by this term.

        Returns:
            HeadTail: Named tuple of head and tail, both `Term` objects.
        """
        head = Term()
        tail = Term()
        self._require_success_expecting_type(
            PL_get_list(self._handle, head._handle, tail._handle),
            'list')
        return self.HeadTail(head=head, tail=tail)

    def get_list_head(self):
        """The head of the list represented by this term.

        Returns:
            Term:
        """
        head = Term()
        self._require_success_expecting_type(
            PL_get_head(self._handle, head._handle),
            'list')
        return head

    def get_list_tail(self):
        """The tail of the list represented by this term.

        Returns:
            Term:
        """
        tail = Term()
        self._require_success_expecting_type(
            PL_get_tail(self._handle, tail._handle),
            'list')
        return tail

    def get_nil(self):
        """Succeeds if this term represents the list termination constant (nil).

        Raises:
            AssertionError: If this term does not represent nil.
        """
        self._require_success(
            PL_get_nil(self._handle))

    def put_variable(self):
        """Put a fresh variable in this term, resetting it to its initial state.
        """
        PL_put_variable(self._handle)

    def put_atom(self, atom):
        """Put an atom in this term.

        Args:
            atom (Atom): Atom to put in this term.
        """
        PL_put_atom(self._handle, atom._handle)

    def put_bool(self, val):
        """Put a boolean in this term.

        Puts either the atom ``true`` or the atom ``false``.
        """
        PL_put_bool(self._handle, int(bool(val)))

    def put_atom_name(self, atom_name):
        """Put an atom in this term, constructed from a string name.

        Args:
            atom_name (str): Name of the atom to put in this term.
        """
        encoded_atom_name = atom_name.encode()
        PL_put_atom_nchars(self._handle,
                           len(encoded_atom_name),
                           encoded_atom_name)

    def put_string(self, string):
        """Put a string in the term."""
        encoded_string = string.encode()
        self._require_success(
            PL_put_string_nchars(self._handle,
                                 len(encoded_string),
                                 encoded_string))

    def put_list_chars(self, bytes_):
        """Put a byte string in the term as a list of characters."""
        self._require_success(
            PL_put_list_nchars(self._handle, len(bytes_), bytes_))

    def put_integer(self, val):
        """Put an integer in the term."""
        self._require_success(
            PL_put_int64(self._handle, val))

    def put_pointer(self, address):
        """Put an integer address in the term."""
        self._require_success(
            PL_put_pointer(self._handle, address))

    def put_float(self, val):
        """Put a floating-point value in the term."""
        self._require_success(
            PL_put_float(self._handle, val))

    def put_functor(self, functor):
        """Put a compound term created from a functor in this term.

        The arguments of the compound term are __TEMPORARY__ variables.
        To create a term with instantiated arguments or with persistent
        variables, use `put_cons_functor`.

        Warning:
            The arguments of the returned compound term are not persistent.
            References to the arguments (e.g. using `get_arg`) may be
            invalidated by the prolog system after other API calls.

            Either use `put_cons_functor` or get a new reference to the
            arguments each time they are needed.
        """
        self._require_success(
            PL_put_functor(self._handle, functor._handle))

    def put_list(self):
        """Put a list pair in this term, whose head and tail are variables.

        Like `put_functor` but using the ``[|]`` functor.
        """
        self._require_success(
            PL_put_list(self._handle))

    def put_nil(self):
        """Put the list terminator constant in this term."""
        self._require_success(
            PL_put_nil(self._handle))

    def put_term(self, term):
        """Set this term to reference the new term."""
        PL_put_term(self._handle, term._handle)

    @classmethod
    def from_term(cls, term):
        """Create a new term as a copy of an existing one."""
        return cls._from_handle(handle=PL_copy_term_ref(term._handle))

    def put_parsed(self, string):
        """Parse `string` as Prolog and place the result in this term.

        Args:
            string (str): A term string in Prolog syntax.
                Optionally ends with a full-stop (.)

        Raises:
            PrologException: If the parse fails.
                The exception is also stored in this term.
        """
        success = PL_chars_to_term(string.encode(), self._handle)
        if not success:
            raise PrologException(self)

    def put_cons_functor(self, functor, *args):
        """Set this term to a compound term created from `functor` and `args`.

        The length of `args` must be the same as the arity of `functor`.
        """
        functor_arity = functor.get_arity()
        if functor_arity != len(args):
            raise TypeError(
                ('Functor arity ({arity}) does not match '
                 'number of arguments ({nargs}).').format(
                     arity=functor_arity, nargs=len(args)))

        if not all(isinstance(arg, Term) for arg in args):
            raise TypeError(
                'All arguments after `functor` must be `Term` objects.')

        if len(args) > 4:
            # PL_cons_functor segfaults when passed > 4 arguments
            return self.put_cons_functor_v(functor, TermList.from_terms(*args))

        self._require_success(
            PL_cons_functor(self._handle, functor._handle,
                            *[arg._handle for arg in args]))

    def put_cons_functor_v(self, functor, args):
        """Set this term to a compound term created from `functor` and args.

        Args:
            functor (Functor): Functor used to create the compound term.
            args (TermList)  : A term list of arguments.
        """
        self._require_success(
            PL_cons_functor_v(self._handle,
                              functor._handle,
                              args._handle))

    def put_cons_list(self, head, tail):
        """Set this term to a list constructed from head and tail."""
        self._require_success(
            PL_cons_list(self._handle, head._handle, tail._handle))

    def put_list_terms(self, terms):
        """Set this term to a list constructed from a list of terms.

        Args:
            terms (list): A (python) list of terms.
        """
        try:
            head = terms.pop(0)
        except IndexError:
            self.put_nil()
            return

        tail = Term.from_nil()
        while terms:
            tail = Term.from_cons_list(terms.pop(), tail)
        self.put_cons_list(head, tail)

    def __call__(self, context_module=None, check=False):
        """Call term like once(term).

        Attempts to find an assignment of the variables in the term that
        makes the term true.

        Args:
            context_module (Module): Context module of the goal.
            check (bool)           : Check that the call succeeded.

        Returns:
            bool: True if the call succeeded.

        Raises:
            PrologCallFailed: If the call failed and `check` is ``True``.
        """
        success = bool(PL_call(self._handle,
                               _get_nullable_handle(context_module)))
        if check and not success:
            raise PrologCallFailed(str(self))
        return success

    def unify(self, term):
        """Unify with a term.

        Functionally equivalent to:
        `Predicate.from_name_arity('=', 2)(self, term)`

        Returns:
            bool: True if the unification was successful

        Even if this returns false, the unification may have partially
        completed and variables will remain bound. Use with `Frame` to
        completely undo bindings in the event of failure.
        """
        return bool(PL_unify(self._handle, term._handle))

    def unify_atom(self, atom):
        """Unify with an atom.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_atom(self._handle, atom._handle))

    def unify_bool(self, val):
        """Unify with a boolean.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_bool(self._handle, int(bool(val))))

    def unify_atom_name(self, atom_name):
        """Unify with an atom given by its name.

        Returns:
            bool: True on success.
        """
        encoded_atom_name = atom_name.encode()
        return bool(PL_unify_atom_nchars(self._handle,
                                         len(encoded_atom_name),
                                         encoded_atom_name))

    def unify_list_chars(self, bytes_):
        """Unify with a list of bytes.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_list_nchars(self._handle, len(bytes_), bytes_))

    def unify_string(self, string):
        """Unify with a string.

        Returns:
            bool: True on success.
        """
        encoded_string = string.encode()
        return bool(PL_unify_string_nchars(self._handle,
                                           len(encoded_string),
                                           encoded_string))

    def unify_integer(self, val):
        """Unify with an integer.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_int64(self._handle, val))

    def unify_float(self, val):
        """Unify with a floating-point value.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_float(self._handle, val))

    def unify_pointer(self, address):
        """Unify with an integer address.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_pointer(self._handle, address))

    def unify_functor(self, functor):
        """Unify with a functor.

        Unifies the functor, not any arguments.
        If functor has arity 0, unifies with an atom.
        Identical to `Term.unify_compound` except for arity-0 functors.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_functor(self._handle, functor))

    def unify_compound(self, functor):
        """Unify with a compound functor.

        Unifies the functor, not any arguments.
        If functor has arity 0, unifies with an arity-0 compound term.
        Identical to `Term.unify_compound` except for arity-0 functors.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_compound(self._handle, functor))

    def unify_list(self, head, tail):
        """Unify with a list cell [head | tail] for terms head, tail.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_list(self._handle, head._handle, tail._handle))

    def unify_nil(self):
        """Unify with the list terminator constant.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_nil(self._handle))

    def unify_arg(self, index, arg):
        """Unify the index-th argument of a compound term with term `arg`.

        Indexing is 0-based.

        Returns:
            bool: True on success.
        """
        return bool(PL_unify_arg(index + 1, self._handle, arg._handle))


def _add_from_method_to_class(klass, put_method_name, put_method):
    suffix = put_method_name[4:]
    from_method_name = 'from_' + suffix
    if hasattr(klass, from_method_name):
        raise AttributeError('{} method already exists.'.format(
            from_method_name))

    def from_method(cls, *args, **kwargs):
        new_term = cls()
        put_method(new_term, *args, **kwargs)
        return new_term

    from_method.__name__ = from_method_name
    from_method.__qualname__ = str(klass.__name__) + '.' + from_method_name
    from_method.__doc__ = 'A new Term initialized using `{}`'.format(
        put_method_name)
    setattr(klass, from_method_name, classmethod(from_method))

# Generate a from_<type> method for each put_<type> method.
for put_method_name in dir(Term):
    if not put_method_name.startswith('put_'):
        continue

    put_method = getattr(Term, put_method_name)

    if not callable(put_method):
        continue
    try:
        _add_from_method_to_class(Term, put_method_name, put_method)
    except AttributeError as e:
        if 'already exists' in str(e):
            # Don't add if from_ already exists.
            pass
        else:
            raise


class TemporaryTerm(Term, TemporaryHandleMixIn):
    pass


class TermList(HandleWrapper):
    """A collection of term references.

    Required by `Term.cons_functor_v` and `Query`.
    """
    def __init__(self, length):
        self._length = length
        super().__init__(handle=PL_new_term_refs(length))

    @classmethod
    def from_terms(cls, *terms):
        termlist = cls(len(terms))
        for i, term in enumerate(terms):
            termlist[i].put_term(term)
        return termlist

    def __eq__(self, other):
        try:
            return super().__eq__(other) and self._length == other._length
        except AttributeError as e:
            if '_handle' not in str(e):
                raise
            return NotImplemented

    def __str__(self):
        return str(list(self))

    def __repr__(self):
        return 'TermList(handle={handle!r}, length={length!r})'.format(
            handle=self._handle,
            length=self._length)

    def __len__(self):
        return self._length

    def __getitem__(self, key):
        if isinstance(key, int) and key >= 0 and key < self._length:
            return Term._from_handle(self._handle + key)
        else:
            raise IndexError()


class Query():
    """Prolog Query Context Manager."""
    _call_predicate = Predicate.from_name_arity('call', 1)

    def __init__(self, predicate, *arguments, arglist=None,
                 goal_context_module=None):
        """Prepare a query.

        A query consists of a predicate (`predicate`) and a list of arguments
        (`arguments`). Each solution is an assignment to variables in
        `arguments` that satisfies the predicate.

        A query behaves statefully. The solutions must be read from
        `arguments`.

        Args:
            predicate (Predicate)       : Predicate to query.
            *arguments (Term)           : Terms to pass as arguments to
                `predicate`.
            arglist (TermList)          : List of argument terms to
                `predicate`. Cannot pass both arguments and arglist.
            goal_context_module (Module): Context module of the goal.
                If ``None``, the current context module is used, or ``user`` if
                there is no context. This only matters for meta_predicates.

        Note
        ----
        Only one query can be active at a time, but the query is not activated
        until `__enter__` is called.
        """
        if arglist is None:
            arglist = TermList.from_terms(*arguments)
        elif arguments:
            raise ValueError('Cannot provide both "arguments" and "arglist".')
        predicate.check_argument_match(arglist)
        self.predicate = predicate
        self.arglist = arglist
        self.goal_context_module = goal_context_module
        self.active_query = None

    @classmethod
    def call_term(cls, term, goal_context_module=None):
        """Prepare a query that will call a single term.

        Args:
            term (Term)                 : Term to call.
            goal_context_module (Module): Context module of the goal.
                If ``None``, the current context module is used, or ``user`` if
                there is no context. This only matters for meta_predicates.

        See `Query.__init__` for more. Equivalent to:
        ``Query(Predicate.from_name_arity('call', 1), term)``
        """
        return cls(Query._call_predicate, term,
                   goal_context_module=goal_context_module)

    def __str__(self):
        return '{pred}({args})'.format(
            pred=str(self.predicate).rsplit('/', 1)[0],
            args=', '.join(str(arg) for arg in self.arglist))

    def __repr__(self):
        return ('Query(predicate={predicate!r}, arglist={arglist!r}, '
                'goal_context_module={goal_context_module!r})').format(
                    predicate=self.predicate,
                    arglist=self.arglist,
                    goal_context_module=self.goal_context_module)

    def __enter__(self):
        self.active_query = _ActiveQuery(self)
        return self.active_query

    def __exit__(self, type, value, traceback):
        self.active_query.close()

    def term_assignments(self, term, persistent):
        """The value of a term under each solution to the query.

        Iterates over all remaining solutions to the query and, for each
        solution, yields the current value of `term`.

        Args:
            term       (Term): The term whose assignments to return.
            persistent (bool): If True, `TermRecord` objects will be yielded
                instead of `TemporaryTerm` so that their value persists
                across solutions.

        Yields:
            Either `TemporaryTerm` or a `TermRecord` representing the
            value of `term` under a particular solution.

            If `persistent` is ``False``, then `TemporaryTerm` values are
            yielded, which are invalidated on the next call to `next_solution`.
        """
        if persistent:
            yield from self._term_assignments_persistent(term)
        else:
            yield from self._term_assignments_temporary(term)

    def _term_assignments_persistent(self, term):
        with self as active_query:
            while active_query.next_solution():
                yield TermRecord(term)

    def _term_assignments_temporary(self, term):
        with self as active_query:
            while active_query.next_solution():
                temporary_term = TemporaryTerm.from_term(term)
                active_query.bind_temporary_term(temporary_term)
                yield temporary_term


class _ActiveQuery(HandleWrapper, TemporaryHandleMixIn):
    """Interface to an active Prolog Query.

    Only one query can be active at a time.
    """
    def __init__(self, query):
        """Create an active query. See `Query`

        Args:
            query (Query) : Query to activate.
        """
        self._query = query
        super().__init__(handle=PL_open_query(
            _get_nullable_handle(query.goal_context_module),
            PL_Q_NODEBUG | PL_Q_CATCH_EXCEPTION,
            query.predicate._handle,
            query.arglist._handle))
        self._bound_temporary_terms = []

    def next_solution(self):
        """Find the next solution, updating `arglist`.

        Returns:
            bool: ``True`` if a solution was found, otherwise returns
                ``False``.

        Raises:
            PrologException: If an exception was raised in Prolog.

        Warning
        -------
        Calling `next_solution` results in backtracking.
        All variable bindings and newly-created terms since the last call
        will be undone.

        Use `TermRecord` to persist terms across backtracks.
        """
        success = bool(PL_next_solution(self._handle))
        self._invalidate_bound_temporary_terms()
        if not success:
            exception_term = PL_exception(self._handle)
            if exception_term:
                raise PrologException(Term._from_handle(exception_term))
        return success

    def bind_temporary_term(self, term):
        """Bind a temporary term to the current solution state of this query.

        The term will be invalidated on the next call to `next_solution`.

        Args:
            term (TemporaryTerm): Temporary term to bind.
        """
        self._bound_temporary_terms.append(term)

    def _invalidate_bound_temporary_terms(self):
        for term in self._bound_temporary_terms:
            term._invalidate()
        self._bound_temporary_terms = []

    def close(self):
        """Close the query and destroy all data and bindings associated with it.
        """
        PL_close_query(self._handle)
        self._invalidate()

    def __str__(self):
        return str(self._query)

    def __repr__(self):
        return ('_ActiveQuery(query={query!r}, _handle={handle!r})'.format(
            query=self._query, _handle=self._handle))


def _get_nullable_handle(handle_wrapper):
    """Return the handle of `handle_wrapper` or None"""
    if handle_wrapper is None:
        return None
    else:
        return handle_wrapper._handle


class TermRecord(HandleWrapper):
    """Records a Prolog Term so that it can be retrieved later.

    This persists across backtracks, unlike `Term` itself.
    """
    def __init__(self, term):
        """Create a term record.

        Args:
            term (Term): Term to record.
        """
        super().__init__(PL_record(term._handle))

    def get(self):
        """Get the term that was stored in this object.

        Returns:
            Term: A copy of the stored term.
        """
        t = Term()
        success = PL_recorded(self._handle, t._handle)
        if not success:
            raise PrologMemoryError()
        return t

    def __del__(self):
        PL_erase(self._handle)


class Frame(HandleWrapper, TemporaryHandleMixIn):
    """A prolog frame context.

    All term references (and optionally, data modifications) created within the
    frame are discarded at the close of the frame.

    With close(), used to create temporary term refences.
    With discard(), used to undo unifications and other data modifications.

    It is best to use the frame in a python context. i.e.:

    >>> X = Term()
    >>> eq = Predicate.from_name_arity('=', 2)
    >>> with Frame() as frame:
    ...     for i in range(3):
    ...         t = frame.term()
    ...         t.put_integer(i)
    ...         eq(X, t) and None
    ...         print(X)
    ...         frame.rewind()
    0
    1
    2

    Warning:
        Term objects created using the `Term` class constructors after the
        frame is opened will produce undefined behaviour (likely segfault) if
        used after the frame is closed, discarded, or rewound.  Instead, use
        the `term()` method to get `Term` objects with proper error handling.

    Warning:
        While the SWI-Prolog documentation doesn't specifically warn against
        it, it is probably a bad idea to open and close multiple frames in
        anything other than stack order.

    Note:
        Frames have no effect on the prolog dynamic database (assertz).
    """
    def __init__(self, discard=False):
        """Open the frame.

        Args:
            discard (bool): If true, __exit__ calls discard() instead of
                close().
        """
        super().__init__(handle=PL_open_foreign_frame())
        self.discard_on_exit = discard
        self._associated_terms = []

    def close(self):
        """Close the frame.

        Discard all term references created since the frame was opened,
        retaining all other prolog data.
        """
        self._invalidate_associated_terms()
        PL_close_foreign_frame(self._handle)
        self._invalidate()

    def discard(self):
        """Discard the frame.

        Discard all term references, bindings, and prolog data created since
        the frame was opened.
        """
        self._invalidate_associated_terms()
        PL_discard_foreign_frame(self._handle)
        self._invalidate()

    def rewind(self):
        """Rewind the frame.

        Undo all bindings and discard all term references created since the
        frame was opened. Does not pop the frame.
        """
        self._invalidate_associated_terms()
        PL_rewind_foreign_frame(self._handle)

    def term(self):
        """Safely create Term objects within this frame.

        The returned terms will be invalidated _in Python_ when this frame is
        closed, discarded, or rewound.

        Term objects created within the frame using the `Term` class will by
        invalidated in Prolog at the end of the frame, but _not_ in Python.
        As a result, continuing to use those objects will produce undefined
        behaviour, likely a segfault.

        Conversely, the `TemporaryTerm` objects returned by this method will
        produce a catachable Python exception if used after invalidation,
        rather than immediately terminating the program with a segfault.
        """
        term = TemporaryTerm()
        self._associated_terms.append(term)
        return term

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.discard_on_exit:
            self.discard()
        else:
            self.close()

    def _invalidate_associated_terms(self):
        for term in self._associated_terms:
            term._invalidate()
        self._associated_terms = []
