"""Read reference data/source records from a checkout or its packaged payload."""
from pathlib import Path


def research_root():
    checkout=Path(__file__).resolve().parents[1]
    if (checkout/'docs/research/pp03/source_reviews_v1.json').is_file():
        return checkout
    from importlib.resources import files
    return Path(str(files('ac.research_data').joinpath('root')))


def source_bytes(relative):
    """Exact distributed public source bytes, never an invented code digest."""
    checkout=Path(__file__).resolve().parent/relative
    if checkout.is_file():return checkout.read_bytes()
    return (research_root()/'ac'/relative).read_bytes()
