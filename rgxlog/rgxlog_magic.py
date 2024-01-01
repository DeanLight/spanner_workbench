# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/04b_spanner_workbench_magic.ipynb.

# %% auto 0
__all__ = ['spanner_workbenchMagic']

# %% ../nbs/04b_spanner_workbench_magic.ipynb 3
from typing import Optional

from IPython.core.magic import (Magics, magics_class, line_cell_magic)

# %% ../nbs/04b_spanner_workbench_magic.ipynb 4
@magics_class
class spanner_workbenchMagic(Magics):
    @line_cell_magic
    def spanner_workbench(self, line: str, cell: Optional[str] = None) -> None:
        # import locally to prevent circular import issues
        from spanner_workbench import magic_session

        if cell:
            magic_session.run_commands(cell, print_results=True)
        else:
            magic_session.run_commands(line, print_results=True)

