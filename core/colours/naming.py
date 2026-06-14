'''
Colour naming via the nearest-neighbour lookup tree.

``rgb_to_name`` resolves the nearest named colour using a KDTree built over the
colour set. That tree (with its parallel ``labels`` list) is stored in the
database as a pickled artifact under ``TREE_KEY``, loaded on first use and
cached for the process (call ``load_tree.cache_clear()`` to force a reload).

This module reads/writes that artifact directly through core.database, so it
sits at the base of the colour domain (core.colours.library calls rgb_to_name)
with no import cycle.
'''

from __future__ import annotations

import functools
import pickle

from sqlalchemy import select

from core.database.engine import session_scope
from core.database.models import ArtifactRecord

TREE_KEY = 'colour_tree'


@functools.cache
def load_tree():
    '''The (tree, labels) pair, read and unpickled from the DB on first use.'''
    with session_scope() as session:
        record = session.scalar(
            select(ArtifactRecord).where(ArtifactRecord.key == TREE_KEY)
        )
    if record is None:
        raise RuntimeError(
            'Colour lookup tree not found in the database. '
            'Run tools/build_tree.ipynb to build it.'
        )
    return pickle.loads(record.data)


def save_tree(tree, labels: list[str]) -> None:
    '''Pickle (tree, labels) into the DB artifact store and refresh the cache.'''
    with session_scope() as session:
        record = session.scalar(
            select(ArtifactRecord).where(ArtifactRecord.key == TREE_KEY)
        )
        if record is None:
            session.add(ArtifactRecord(key=TREE_KEY, data=pickle.dumps((tree, labels))))
        else:
            record.data = pickle.dumps((tree, labels))
    load_tree.cache_clear()  # next load reads the just-written tree


def rgb_to_name(rgb: tuple[int, int, int]) -> str:
    tree, labels = load_tree()
    _, ind = tree.query(rgb, k=1)
    return labels[ind]
