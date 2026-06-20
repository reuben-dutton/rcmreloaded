'''
The interactions service: a session-free entry point to the Bluesky theme-vote
features.

The ``votes`` repository is the session-taking query layer (every function
takes a ``Session``). This service owns its own sessions, so callers outside
the domain - ``post.py`` / ``generate`` - can read the winning theme without
managing one:

    from core.interactions import InteractionsService

    interactions = InteractionsService()
    theme = interactions.vote.active         # the active winning Theme, or None
    if theme is not None:
        Pipeline().filter(theme).random()

Everything returned is detached from the database session that produced it.
'''

from __future__ import annotations

from core.database import session_scope
from core.interactions.votes import current_theme_vote
from core.themes import Theme as ThemeContainer, themes


class VoteService:
    '''Session-free access to the live theme vote.'''

    @property
    def active(self) -> ThemeContainer | None:
        '''
        The winning theme while it is active.

        Returns the winning option's :class:`~core.themes.Theme` during the
        theme-active window (``theme_start_date <= now <= theme_end_date``),
        ready to hand to ``Pipeline.filter``. Returns ``None`` otherwise - no
        current vote, still in the voting window, no votes tallied, or the
        winning theme is no longer in the library.
        '''
        with session_scope() as session:
            vote = current_theme_vote(session)
        if vote is None or not vote.active:
            return None
        winner = vote.winner
        return themes.get(winner.theme_tag) if winner is not None else None


class InteractionsService:
    '''
    Entry point to the interactions domain. Accessors are grouped by feature -
    for now just ``vote`` - so callers read e.g. ``service.vote.active``.
    '''

    def __init__(self):
        self.vote = VoteService()
