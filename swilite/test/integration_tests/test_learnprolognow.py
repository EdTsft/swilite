# Tests based on the content of "Learn Prolog Now"
# http://www.learnprolognow.org/

from nose.tools import assert_true, assert_false, assert_equal

from swilite.prolog import Atom, Functor, Term, TermList, Predicate, Query

class TestLearnPrologNowCh1():
    # http://www.learnprolognow.org/lpnpage.php?pagetype=html&pageid=lpn-htmlse1
    def setup(self):
        self.retractall = Predicate.from_name_arity('retractall', 1)
        self.assertz = Predicate.from_name_arity('assertz', 1)
        self.dynamic = Predicate.from_name_arity('dynamic', 1)
        self.rule = Functor(':-', 2)
        self.and_ = Functor(',', 2)

    def knowledge_database_1(self):
        woman = Functor('woman', 1)
        plays_air_guitar = Functor('playsAirGuitar', 1)
        mia = Term.from_atom_name('mia')
        jody = Term.from_atom_name('jody')
        yolanda = Term.from_atom_name('yolanda')
        party = Term.from_atom_name('party')
        rock_concert = Term.from_atom_name('rockConcert')

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
        happy = Functor('happy', 1)
        listens_2_music = Functor('listens2Music', 1)
        plays_air_guitar = Functor('playsAirGuitar', 1)

        mia = Term.from_atom_name('mia')
        yolanda = Term.from_atom_name('yolanda')

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
        happy = Functor('happy', 1)
        listens_2_music = Functor('listens2Music', 1)
        plays_air_guitar = Functor('playsAirGuitar', 1)

        vincent = Term.from_atom_name('vincent')
        butch = Term.from_atom_name('butch')

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
        woman = Functor('woman', 1)
        loves = Functor('loves', 2)

        self.retractall(woman(Term()))
        self.retractall(loves(Term(), Term()))

        mia = Term.from_atom_name('mia')
        jody = Term.from_atom_name('jody')
        yolanda = Term.from_atom_name('yolanda')
        vincent = Term.from_atom_name('vincent')
        butch = Term.from_atom_name('butch')
        marsellus = Term.from_atom_name('marsellus')
        honey_bunny = Term.from_atom_name('honey_bunny')
        pumpkin = Term.from_atom_name('pumpkin')

        self.dynamic(Term.from_functor(woman))
        self.dynamic(Term.from_functor(loves))

        self.assertz(woman(mia))
        self.assertz(woman(jody))
        self.assertz(woman(yolanda))

        self.assertz(loves(vincent, mia))
        self.assertz(loves(marsellus, mia))
        self.assertz(loves(pumpkin, honey_bunny))
        self.assertz(loves(honey_bunny, pumpkin))

        X = Term()
        # Creates a compound term: woman(X)
        # Then evaluates that compound term like once(woman(X))
        # Finds the first solution.
        woman(X)()
        assert_equal(X, mia)

        # Do the same thing by calling a predicate instead of evaluating
        # a compound term.
        # Creates the predicate `woman` then evaluates it with the argument `Y`
        # Again, finds the first solution.
        Y = Term()
        Predicate(woman)(Y)
        assert_equal(Y, mia)

        # Use a query to find all solutions.
        Z = Term()
        with Query(Predicate(woman), Z) as q:
            q.next_solution()
            assert_equal(Z, mia)
            q.next_solution()
            assert_equal(Z, jody)
            q.next_solution()
            assert_equal(Z, yolanda)
            assert_false(q.next_solution())

        X.put_variable()
        assert_true((loves(marsellus, X) & woman(X))())
        assert_equal(X, mia)

    def knowledge_database_5(self):
        loves = Functor('loves', 2)
        jealous = Functor('jealous', 2)

        self.retractall(loves(Term(), Term()))
        self.retractall(jealous(Term(), Term()))

        mia = Term.from_atom_name('mia')
        vincent = Term.from_atom_name('vincent')
        marsellus = Term.from_atom_name('marsellus')
        honey_bunny = Term.from_atom_name('honey_bunny')
        pumpkin = Term.from_atom_name('pumpkin')

        self.assertz(loves(vincent, mia))
        self.assertz(loves(marsellus, mia))
        self.assertz(loves(pumpkin, honey_bunny))
        self.assertz(loves(honey_bunny, pumpkin))
        X = Term()
        Y = Term()
        Z = Term()
        self.assertz(self.rule(jealous(X, Y), loves(X, Z) & loves(Y, Z)))
        print(self.rule(jealous(X, Y), loves(X, Z) & loves(Y, Z)))

        W = Term()
        jealous(marsellus, W)()
        assert_equal(W, vincent)
