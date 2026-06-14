'''
The interactions domain: Bluesky/atproto-facing functionality.

Currently this is theme votes - see core.interactions.votes. The
``InteractionsService`` is the session-free entry point callers use to read the
active winning theme (e.g. ``InteractionsService().vote.current``).
'''

from core.interactions.service import InteractionsService, VoteService

__all__ = [
    'InteractionsService',
    'VoteService',
]
