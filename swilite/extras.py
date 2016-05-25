from .prolog import Term, Functor, Atom, Predicate


def consult(filename):
    """Consult a prolog file, importing its public predicates."""
    Term.from_cons_functor(
        Functor(Atom('consult'), 1),
        Term.from_atom_name(filename))()

def make_list_term(*terms):
    """Combine multiple terms into a single list.

    Args:
        *terms (prolog.Term) : Terms to combine into a list.
    """
    list_term = Term.from_nil()

    for term in reversed(terms):
        list_term = Term.from_cons_list(term, list_term)
    return list_term
