'''
Colour helpers, split so the import graph stays acyclic:

  - db.utils.convert : pure RGB <-> hex, depended on by db.models and db.schemas
  - db.utils.naming  : rgb_to_name + the DB-backed lookup tree

This package __init__ intentionally imports nothing: importing db.utils.convert
must not drag in db.utils.naming (which imports db.models), or db.models'
import of convert would cycle. Import from the submodules directly.
'''
