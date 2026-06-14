'''
Empty the theme-vote tables (``theme_options`` then ``theme_votes``).

A small maintenance helper for clearing out test votes. Deletes every row from
both tables - the child ``theme_options`` first to respect the foreign key -
and leaves every other table (themes, colours, artifacts) untouched.

Usage (from anywhere):

    python tools/clear_theme_votes.py        # asks for confirmation first
    python tools/clear_theme_votes.py -y     # skip the confirmation
'''

import argparse
import sys
import pathlib

# allow importing the project's packages no matter where this is run from
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select

from core.database import session_scope
from core.database.models import ThemeOptionRecord, ThemeVoteRecord


def _counts(session) -> tuple[int, int]:
    '''(theme_votes, theme_options) row counts.'''
    votes = session.scalar(select(func.count()).select_from(ThemeVoteRecord))
    options = session.scalar(select(func.count()).select_from(ThemeOptionRecord))
    return votes, options


def clear_theme_votes() -> tuple[int, int]:
    '''Delete every vote and option; returns how many of each were removed.'''
    with session_scope() as session:
        votes, options = _counts(session)
        session.execute(delete(ThemeOptionRecord))  # child first (FK)
        session.execute(delete(ThemeVoteRecord))
    return votes, options


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-y', '--yes', action='store_true',
        help='delete without asking for confirmation',
    )
    args = parser.parse_args()

    with session_scope() as session:
        votes, options = _counts(session)
    print(f'theme_votes={votes}, theme_options={options}')

    if votes == 0 and options == 0:
        print('already empty - nothing to do')
        return

    if not args.yes:
        try:
            reply = input('Delete all of the above? [y/N] ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            reply = ''
        if reply not in ('y', 'yes'):
            print('\naborted')
            return

    votes, options = clear_theme_votes()
    print(f'deleted {votes} vote(s) and {options} option(s)')


if __name__ == '__main__':
    main()
