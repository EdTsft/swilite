# Tests based on the content of "Learn Prolog Now"
# http://www.learnprolognow.org/

from nose.tools import assert_true, assert_false, assert_equal

from swilite.prolog import (Atom, Functor, Term, TermList, Predicate, Query,
                            Frame)

# Common terms
happy = Functor('happy', 1)
jealous = Functor('jealous', 2)
listens_2_music = Functor('listens2Music', 1)
loves = Functor('loves', 2)
plays_air_guitar = Functor('plays_air_guitar', 1)
woman = Functor('woman', 1)

mia = Term.from_atom_name('mia')
jody = Term.from_atom_name('jody')
yolanda = Term.from_atom_name('yolanda')

vincent = Term.from_atom_name('vincent')
butch = Term.from_atom_name('butch')
marcellus = Term.from_atom_name('marcellus')
honey_bunny = Term.from_atom_name('honey_bunny')

pumpkin = Term.from_atom_name('pumpkin')

party = Term.from_atom_name('party')
rock_concert = Term.from_atom_name('rockConcert')


class BasicKeywords():
    def setup(self):
        self.retractall = Predicate.from_name_arity('retractall', 1)
        self.assertz = Predicate.from_name_arity('assertz', 1)
        self.dynamic = Predicate.from_name_arity('dynamic', 1)
        self.call = Predicate.from_name_arity('call', 1)
        self.rule = Functor(':-', 2)


class TestLearnPrologNowCh1(BasicKeywords):
    # http://www.learnprolognow.org/lpnpage.php?pagetype=html&pageid=lpn-htmlse1

    def knowledge_database_1(self):
        self.dynamic(Term.from_functor(woman))
        self.dynamic(rock_concert)
        self.assertz(woman(mia))
        self.assertz(woman(jody))
        self.assertz(woman(yolanda))
        self.assertz(plays_air_guitar(jody))
        self.assertz(party)

        assert_true(woman(mia)())
        assert_true(woman(jody)())
        assert_true(woman(yolanda)())
        assert_false(woman(Term.from_atom_name('bob'))())

        once = Functor('once', 1)
        once_pred = Predicate(once)
        assert_true(once_pred(woman(mia)))
        once_pred(woman(mia), check=True)
        assert_false(once_pred(woman(Term.from_atom_name('bob'))))

        assert_true(plays_air_guitar(jody)())
        assert_false(plays_air_guitar(mia)())

        assert_true(party())
        assert_false(Term.from_atom_name('rockConcert')())

    def knowledge_database_2(self):
        self.dynamic(Term.from_functor(happy))
        self.dynamic(Term.from_functor(listens_2_music))
        self.dynamic(Term.from_functor(plays_air_guitar))

        self.assertz(happy(yolanda))
        self.assertz(listens_2_music(mia))
        self.assertz(self.rule(listens_2_music(yolanda), happy(yolanda)))
        self.assertz(self.rule(plays_air_guitar(mia), listens_2_music(mia)))
        self.assertz(self.rule(plays_air_guitar(yolanda),
                               listens_2_music(yolanda)))

        assert_true(plays_air_guitar(mia)())

    def knowledge_database_3(self):
        self.dynamic(Term.from_functor(happy))
        self.dynamic(Term.from_functor(listens_2_music))
        self.dynamic(Term.from_functor(plays_air_guitar))

        self.assertz(happy(vincent))
        self.assertz(listens_2_music(butch))
        self.assertz(self.rule(plays_air_guitar(vincent),
                               self.and_(listens_2_music(vincent),
                                         happy(vincent))))
        self.assertz(self.rule(plays_air_guitar(butch), happy(butch)))
        self.assertz(self.rule(plays_air_guitar(butch), listens_2_music(butch)))

        assert_false(plays_air_guitar(vincent)())
        assert_true(plays_air_guitar(butch)())

    def knowledge_database_4(self):
        self.retractall(woman(Term()))
        self.retractall(loves(Term(), Term()))

        self.dynamic(Term.from_functor(woman))
        self.dynamic(Term.from_functor(loves))

        self.assertz(woman(mia))
        self.assertz(woman(jody))
        self.assertz(woman(yolanda))

        self.assertz(loves(vincent, mia))
        self.assertz(loves(marcellus, mia))
        self.assertz(loves(pumpkin, honey_bunny))
        self.assertz(loves(honey_bunny, pumpkin))

        with Frame() as f:
            X = f.term()
            # Creates a compound term: woman(X)
            # Then evaluates that compound term like once(woman(X))
            # Finds the first solution.
            woman(X)()
            assert_equal(X, mia)

        with Frame() as f:
            # Do the same thing by calling a predicate instead of evaluating
            # a compound term.
            # Creates the predicate `woman` then evaluates it with the argument
            # `X`. Again, finds the first solution.
            X = f.term()
            Predicate(woman)(X)
            assert_equal(X, mia)

            # Use a query to find all solutions.
        with Frame() as f:
            X = f.term()
            with Query(Predicate(woman), X) as q:
                q.next_solution()
                assert_equal(X, mia)
                q.next_solution()
                assert_equal(X, jody)
                q.next_solution()
                assert_equal(X, yolanda)
                assert_false(q.next_solution())

        with Frame() as f:
            X = f.term()
            assert_true((loves(marcellus, X) & woman(X))())
            assert_equal(X, mia)

    def knowledge_database_5(self):
        self.retractall(loves(Term(), Term()))
        self.retractall(jealous(Term(), Term()))

        self.assertz(loves(vincent, mia))
        self.assertz(loves(marcellus, mia))
        self.assertz(loves(pumpkin, honey_bunny))
        self.assertz(loves(honey_bunny, pumpkin))
        X = Term()
        Y = Term()
        Z = Term()
        self.assertz(self.rule(jealous(X, Y), loves(X, Z) & loves(Y, Z)))

        W = Term()
        jealous(marcellus, W)()
        assert_equal(W, vincent)


class TestLearnPrologNowCh2(BasicKeywords):
    # http://www.learnprolognow.org/lpnpage.php?pagetype=html&pageid=lpn-htmlch2
    def test_basic_unification(self):
        assert_true(mia.unify(mia))

        two = Term.from_integer(2)
        assert_true(two, two)

        assert_false(mia.unify(vincent))

        with Frame():
            assert_true(Term().unify(mia))

        with Frame():
            assert_true(Term().unify(Term()))

        with Frame():
            X = Term()
            assert_true(X.unify(mia))
            assert_false(X.unify(vincent))

        k = Functor('k', 2)
        s = Functor('s', 1)
        t = Functor('t', 1)
        g = Term.from_atom_name('g')
        k_atom = Term.from_atom_name('k')

        with Frame():
            X = Term()
            Y = Term()

            assert_true(k(s(g), Y).unify(k(X, t(k_atom))))
            assert_equal(X, s(g))
            assert_equal(Y, t(k_atom))

        with Frame():
            X = Term()
            Y = Term()

            assert_true(k(s(g), t(k_atom)).unify(k(X, t(Y))))
            assert_equal(X, s(g))
            assert_equal(Y, k_atom)

        self.retractall(loves(Term(), Term()))
        self.assertz(loves(vincent, mia))
        self.assertz(loves(marcellus, mia))
        self.assertz(loves(pumpkin, honey_bunny))
        self.assertz(loves(honey_bunny, pumpkin))

        with Frame():
            X = Term()
            assert_false(loves(X, X).unify(loves(marcellus, mia)))

    def test_lines_example(self):
        point = Functor('point', 2)
        line = Functor('line', 2)
        vertical = Functor('vectical', 1)
        horizontal = Functor('horizontal', 1)

        with Frame():
            X = Term()
            Y = Term()
            Z = Term()
            self.assertz(vertical(line(point(X, Y), point(X, Z))))
            self.assertz(horizontal(line(point(X, Y), point(Z, Y))))

        _1 = Term.from_integer(1)
        _2 = Term.from_integer(2)
        _3 = Term.from_integer(3)
        assert_true(vertical(line(point(_1, _1), point(_1, _3)))())
        assert_false(vertical(line(point(_1, _1), point(_3, _2)))())

        with Frame():
            Y = Term()
            assert_true(horizontal(line(point(_1, _1), point(_2, Y)))())
            assert_equal(Y, _1)

        with Frame():
            P = Term()
            expr = horizontal(line(point(_2, _3), P))
            with Query(self.call, expr) as q:
                res = list(q.term_assignments(P, True))
            assert_equal(len(res), 1)
            assert_true(res[0].get().unify(point(Term(), _3)))
