from __future__ import annotations

from dataclasses import dataclass

from ac.logic.fo import Formula
from ac.logic.predicates import WordPredicate


@dataclass(frozen=True)
class FormulaPredicate(WordPredicate):
    """Bridge a closed AC finite-logic formula into the WordPredicate layer."""

    formula: Formula

    def holds(self, word) -> bool:
        return self.formula.holds(word)
