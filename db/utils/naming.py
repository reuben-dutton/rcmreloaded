'''
Colour naming via the nearest-neighbour lookup tree.

``rgb_to_name`` resolves the nearest named colour using a KDTree built over the
colour set. That tree (with its parallel ``labels`` list) is stored in the
database as a pickled artifact under ``TREE_KEY``, loaded on first use and
cached for the process.

This module reads/writes that artifact directly through db.engine + db.models
rather than through db.repository, so it sits below schemas/repository in the
import graph (db.schemas.Colour depends on rgb_to_name) and forms no cycle.
'''

from __future__ import annotations

import pickle
import typing

from sqlalchemy import select

from db.engine import session_scope
from db.models import ArtifactRecord

TREE_KEY = 'colour_tree'

# process-wide cache of the unpickled (tree, labels) pair
_tree: typing.Any = None
_labels: list[str] | None = None


def load_tree(force: bool = False):
    '''Return the cached (tree, labels), reading them from the DB on first use.'''
    global _tree, _labels
    if _tree is None or force:
        with session_scope() as session:
            record = session.scalar(
                select(ArtifactRecord).where(ArtifactRecord.key == TREE_KEY)
            )
        if record is None:
            raise RuntimeError(
                'Colour lookup tree not found in the database. '
                'Run tools/build_tree.ipynb to build it.'
            )
        _tree, _labels = pickle.loads(record.data)
    return _tree, _labels


def save_tree(tree, labels: list[str]) -> None:
    '''Pickle (tree, labels) into the DB artifact store and refresh the cache.'''
    global _tree, _labels
    with session_scope() as session:
        record = session.scalar(
            select(ArtifactRecord).where(ArtifactRecord.key == TREE_KEY)
        )
        if record is None:
            session.add(ArtifactRecord(key=TREE_KEY, data=pickle.dumps((tree, labels))))
        else:
            record.data = pickle.dumps((tree, labels))
    _tree, _labels = tree, labels


def rgb_to_name(rgb: tuple[int, int, int]) -> str:
    tree, labels = load_tree()
    _, ind = tree.query(rgb, k=1)
    return labels[ind]
