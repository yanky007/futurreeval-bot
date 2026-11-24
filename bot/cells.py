"""The 3x3 grid: which dossier and which model each of the 9 forecasts uses."""
from contextvars import ContextVar
from dataclasses import dataclass

from bot import config as cfg


@dataclass(frozen=True)
class Cell:
    dossier: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.dossier}x{self.model}"


# Set while one forecast runs, so get_llm("default") can return that cell's model.
CURRENT_CELL: ContextVar[Cell | None] = ContextVar("current_cell", default=None)


def assign_cell(k: int, available_dossiers: list[str]) -> Cell:
    """Map forecast number k (0..8) to a cell. If a dossier failed, its
    cells are re-pointed at the dossiers that succeeded, keeping the model."""
    if not available_dossiers:
        raise ValueError("No dossiers available")
    d_idx, m_idx = divmod(k % 9, 3)
    dossier = cfg.DOSSIERS[d_idx]
    if dossier not in available_dossiers:
        dossier = available_dossiers[d_idx % len(available_dossiers)]
    return Cell(dossier=dossier, model=cfg.MODELS[m_idx])
