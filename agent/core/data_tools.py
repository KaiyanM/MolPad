"""The data side of the agent in one import: the Dataset and the Session.

The Session is the base of agent/core/session.py plus the data operations of every module
(agent/modules/<name>/ops.py). Session.OPS lists the operations by name.
"""

from .dataset import (COVER_SHARE, DEFAULT_TOP, Dataset, _py, load_dataset,  # noqa: F401
                           use_dataset)
from .module import modules
from .session import MissingInput, SessionBase  # noqa: F401


def _session_class():
    mods = [m for m in modules() if m.Ops is not None]
    return type("Session", tuple(m.Ops for m in mods) + (SessionBase,),
                {"__doc__": SessionBase.__doc__, "OPS": tuple(o for m in mods for o in m.ops)})


Session = _session_class()
