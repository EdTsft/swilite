# Tests based on the content of "Learn Prolog Now"
# http://www.learnprolognow.org/

from nose.tools import assert_true, assert_false

from swilite.prolog import Atom, Functor, Term, TermList, Predicate

class TestLearnPrologNow():
    # http://www.learnprolognow.org/lpnpage.php?pagetype=html&pageid=lpn-htmlse1
    def setup(self):
        self.assertz = Predicate(Functor('assertz', 1))
        self.dynamic = Predicate(Functor('dynamic', 1))
        self.rule = Functor(':-', 2)
        self.and_ = Functor(',', 2)

    def test_ch_1_1_kb_1(self):
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

    def test_ch_1_1_kb_2(self):
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

    def test_ch_1_1_kb_3(self):
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

    def test_ch_1_1_kb_4(self):
        woman = Functor('woman', 1)
        loves = Functor('loves', 2)

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
        self.assertz(yolanda))

        self.assertz(loves(vincent, mia))
        self.assertz(loves(marsellus, mia))
        self.assertz(loves(pumpkin, honey_bunny))
        self.assertz(loves(honey_bunny, pumpkin))

        X = Term()

