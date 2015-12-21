import copy

from nose.tools import assert_equal, assert_not_equal

from swilite.prolog import (Atom, Functor, Module, Predicate, Term)


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


def test_term__init__():
    t = Term()
    assert_equal(t.type(), 'variable')
