import copy

from nose.tools import (assert_equal, assert_not_equal, assert_raises,
                        assert_true, assert_false)

from swilite.prolog import (Atom, CallError, Functor, Module, Predicate, Term,
                            TermList, Frame)


def check_atom(name, atom=None):
    if atom is None:
        atom = Atom(name)

    assert_equal(str(atom), name)
    assert_equal(repr(atom), 'Atom(name={!r})'.format(name))
    assert_equal(atom.get_name(), name)
    assert_equal(hash(atom), hash(Atom(name)))
    assert_equal(atom, atom)
    assert_equal(atom, Atom(name))


def test_atom():
    a = Atom('a')
    check_atom('a', a)

    copy_a = copy.copy(a)
    assert_equal(a, copy_a)
    check_atom('a', copy_a)

    check_atom('')
    check_atom('X')
    check_atom('ab')
    check_atom('_')
    check_atom('abcdefghij')


def test_atom__ne__():
    assert_not_equal(Atom('a'), Atom('b'))
    assert_not_equal(Atom('a'), Atom('A'))
    assert_not_equal(Atom('a'), Atom('ab'))


def test_atom_del():
    a = Atom('a')
    del a
    a = Atom('a')
    del a
    b = Atom('b')
    del b


def test_atom_del_multiple():
    a = Atom('a')
    b = Atom('b')
    c = Atom('a')
    del a
    del b
    del c


def test_atom_del_after_ref_copy():
    a = Atom('a')
    b = a
    del a
    del b


def test_atom_del_after_copy():
    a = Atom('a')
    b = copy.copy(a)
    del a
    del b

    a = Atom('a')
    b = copy.copy(a)
    del b
    del a


def check_functor(name, arity, functor=None):
    if functor is None:
        functor = Functor(name, arity)
    if isinstance(name, str):
        name = Atom(name)

    # Test __str__
    assert_equal(str(functor),
                 '{name!s}/{arity!s}'.format(name=name, arity=arity))
    # Test __repr__
    assert_equal(repr(functor),
                 'Functor(name={name!r}, arity={arity!r})'.format(
                     name=name, arity=arity))

    # Test get_name and get_arity
    assert_equal(functor.get_name(), name)
    assert_equal(functor.get_arity(), arity)

    # Test __eq__ and __init__
    assert_equal(functor, functor)
    assert_equal(functor, Functor(name, arity))
    assert_equal(functor, Functor(str(name), arity))

    # Test __hash__
    assert_equal(hash(functor), hash(Functor(name, arity)))


def test_functor():
    check_functor(Atom('a'), 0)
    check_functor(Atom('a'), 1)
    check_functor(Atom('a'), 2)
    check_functor(Atom('a'), 10)
    check_functor('a', 2)
    check_functor('', 2)
    check_functor(Atom(''), 2)
    check_functor(Atom('Abc'), 2)
    check_functor('_Abc', 2)


def test_functor__ne__():
    assert_not_equal(Functor(Atom('a'), 1), Functor(Atom('b'), 1))
    assert_not_equal(Functor(Atom('a'), 1), Functor(Atom('a'), 2))
    assert_not_equal(Functor(Atom('a'), 1), Functor(Atom('a'), 0))
    assert_not_equal(Functor(Atom('a'), 0), Atom('a'))


def check_module(name, module=None):
    if isinstance(name, str):
        name = Atom(name)
    if module is None:
        module = Module(name)

    assert_equal(str(module), str(name))
    assert_equal(repr(module), 'Module(name={!r})'.format(name))
    assert_equal(module.get_name(), name)
    assert_equal(hash(module), hash(Module(name)))
    assert_equal(module, module)
    assert_equal(module, Module(name))


def test_module():
    check_module('a')
    check_module('_')
    check_module('Ab')


def test_module_current_context():
    check_module('user', Module.current_context())


def test_predicate__eq__str__repr():
    foo2 = Functor('foo', 2)
    mod = Module(Atom('mod'))

    foo2_no_module = Predicate(foo2)
    foo2_mod = Predicate(foo2, mod)
    foo2_no_module_name_arity = Predicate.from_name_arity('foo', 2)

    assert_equal(foo2_no_module, foo2_no_module_name_arity)
    assert_not_equal(foo2_no_module, foo2_mod)
    assert_not_equal(foo2_no_module_name_arity, foo2_mod)
    assert_equal(foo2_no_module, foo2_no_module)
    assert_equal(foo2_mod, foo2_mod)
    assert_equal(foo2_no_module_name_arity, foo2_no_module_name_arity)

    assert_equal(str(foo2_no_module), 'user:foo/2')
    assert_equal(str(foo2_no_module_name_arity), 'user:foo/2')
    assert_equal(str(foo2_mod), 'mod:foo/2')

    assert_equal(repr(foo2_no_module),
                 'Predicate(functor={functor!r}, module={module!r})'.format(
                     functor=foo2, module=Module.current_context()))
    assert_equal(repr(foo2_mod),
                 'Predicate(functor={functor!r}, module={module!r})'.format(
                     functor=foo2, module=mod))


def check_predicate(name, arity, module=None, predicate=None):
    if isinstance(name, str):
        name = Atom(name)
    if isinstance(module, str):
        module = Module(Atom(module))

    module_str = str(module) if module is not None else None

    if predicate is None:
        print(repr(module_str))
        check_predicate(name=name, arity=arity, module=module,
                        predicate=Predicate.from_name_arity(
                            name=str(name), arity=arity, module_name=module_str)
                        )
        check_predicate(name=name, arity=arity, module=module,
                        predicate=Predicate(
                            functor=Functor(name=name, arity=arity),
                            module=module))
        return

    stored_module = Module.current_context() if module is None else module

    assert_equal(str(predicate), '{module!s}:{name!s}/{arity!s}'.format(
        module=stored_module, name=name, arity=arity))
    assert_equal(repr(predicate),
                 'Predicate(functor={functor!r}, module={module!r})'.format(
                     functor=Functor(name=name, arity=arity),
                     module=stored_module))

    info = predicate.get_info()
    assert_equal(info.name, name)
    assert_equal(info.arity, arity)
    assert_equal(info.module, stored_module)

    assert_equal(predicate, predicate)
    assert_equal(predicate, Predicate(functor=Functor(name, arity),
                                      module=module))
    assert_equal(predicate,
                 Predicate.from_name_arity(str(name), arity, module_str))

    assert_equal(hash(predicate), hash(Predicate(functor=Functor(name, arity),
                                                 module=module)))


def test_predicate():
    check_predicate('foo', 2)
    check_predicate('foo', 2, 'mod')
    check_predicate('Abc', 2)
    check_predicate('', 2)
    check_predicate('foo', 1)
    check_predicate('foo', 0)


def check_predicate_call_succ(a, b, check, variable):
    succ = Predicate(Functor('succ', 2))

    args = TermList(2)
    if variable == 'first':
        args[1].put_integer(b)
    elif variable == 'second':
        args[0].put_integer(a)
    elif variable == 'none':
        args[0].put_integer(a)
        args[1].put_integer(b)
    else:
        assert False

    if not check:
        result = succ(arglist=args)
        assert_equal(result, variable != 'none' or (a + 1) == b)
    elif variable == 'none' and (a + 1) != b:
        with assert_raises(CallError):
            succ(arglist=args, check=True)
    else:
        succ(arglist=args, check=True)

    if variable == 'first':
        assert_equal(int(args[0]), b - 1)
    elif variable == 'second':
        assert_equal(int(args[1]), a + 1)


def test_predicate__call__():
    for (a, b) in [(0, 1), (4, 5), (0, 2), (5, 4)]:
        for check in [True, False]:
            for variable in ['first', 'second', 'none']:
                yield check_predicate_call_succ, a, b, check, variable


def test_term__init__():
    t = Term()
    assert_equal(t.type(), 'variable')

def test_term_atom():
    foo = Term.from_atom_name('foo')
    assert_equal(foo.type(), 'atom')
    assert_equal(str(foo), 'foo')

def test_term__eq__():
    foo = Term.from_atom_name('foo')
    assert foo == foo


def test_term_equality():
    a = Term.from_atom_name('a')
    b = Term.from_atom_name('b')
    eq = Predicate.from_name_arity('=', 2)

    assert_true(eq(a, a))
    assert_false(eq(a, b))


def test_term_variable_assignment():
    a = Term.from_atom_name('a')
    b = Term.from_atom_name('b')
    eq = Predicate.from_name_arity('=', 2)

    X = Term()
    assert_true(eq(X, a))
    assert_equal(X, a)
    assert_false(eq(X, b))

    assert_true(eq(Term(), b))

    X.put_variable()
    assert_true(eq(X, b))

def test_term__or__():
    a = Term.from_atom_name('a')
    b = Term.from_atom_name('b')
    eq = Functor('=', 2)

    assert_true((eq(a, b) | eq(a, a))())
    assert_false((eq(a, b) | eq(b, a))())
    X = Term()
    assert_true((eq(X, a) | eq(X, b))())
    assert X == a or X == b

    assert_equal(str(eq(a, a) | eq(a, b)), 'a=a;a=b')

def test_term__and__():
    a = Term.from_atom_name('a')
    b = Term.from_atom_name('b')
    eq = Functor('=', 2)

    assert_true((eq(a, a) & eq(b, b))())
    assert_false((eq(a, b) & eq(a, a))())
    assert_false((eq(a, a) & eq(a, b))())

    X = Term()
    Y = Term()
    assert_true((eq(X, a) & eq(Y, a) & eq(X, Y))())
    assert_equal(X, Y)
    X.put_variable()
    Y.put_variable()
    assert_false((eq(X, a) & eq(X, b))())

    assert_equal(str(eq(a, a) & eq(a, b)), 'a=a,a=b')

def test_term_logic():
    true = Term.from_atom_name('true')
    false = Term.from_atom_name('false')

    assert_true(true())
    assert_false(false())
    assert_true((true | false)())
    assert_false((true & false)())
    assert_false((false & true | false)())
    assert_true((false & false | true)())
    assert_false((false & (false | true))())


def test_frame_close():
    f1 = Frame()
    t1 = f1.term()
    t1.put_atom_name('t1')
    assert_equal(str(t1), 't1')
    f1.close()
    with assert_raises(AttributeError):
        print(t1)
    with assert_raises(AttributeError):
        f1.close()

    with Frame() as f2:
        t2 = f2.term()
        t2.put_atom_name('t2')
        assert_equal(str(t2), 't2')

    with assert_raises(AttributeError):
        print(t2)
    with assert_raises(AttributeError):
        f2.close()

    X = Term()
    with Frame():
        X.put_integer(1)
        assert_equal(str(X), '1')
    assert_equal(str(X), '1')

    eq = Predicate.from_name_arity('=', 2)
    X = Term()
    with Frame():
        eq(X, Term.from_integer(1))
        assert_equal(str(X), '1')
    assert_equal(str(X), '1')


def test_frame_discard():
    eq = Predicate.from_name_arity('=', 2)

    X = Term()
    with Frame(discard=True):
        X.put_integer(1)
        assert_equal(str(X), '1')
    assert_equal(str(X), '1')

    X = Term()
    with Frame(discard=True):
        eq(X, Term.from_integer(1))
        assert_equal(str(X), '1')
        assert_equal(X.type(), 'integer')
    assert_not_equal(str(X), '1')
    assert_equal(X.type(), 'variable')

def test_frame_rewind():
    eq = Predicate.from_name_arity('=', 2)
    two = Term.from_integer(2)
    three = Term.from_integer(3)

    X = Term()
    with Frame() as f:
        t = f.term()
        t.put_integer(1)
        eq(X, two)
        assert_equal(t, Term.from_integer(1))
        assert_equal(X, two)

        f.rewind()
        with assert_raises(AttributeError):
            print(str(t))

        assert_equal(X.type(), 'variable')
        eq(X, three)
        assert_equal(X, three)
        f.rewind()
        assert_equal(X.type(), 'variable')
        eq(X, two)

    assert_equal(X, two)

def test_frame_dynamic_database():
    dynamic = Predicate.from_name_arity('dynamic', 1)
    assertz = Predicate.from_name_arity('assertz', 1)

    foo = Functor('foo', 1)
    a = Term.from_atom_name('a')

    dynamic(foo(Term()))

    with Frame(discard=True):
        assertz(foo(a))
        assert_true(foo(a)())

    # Frames have no effect on the dynamic database
    assert_true(foo(a)())
