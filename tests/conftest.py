from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "grammars"


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES
