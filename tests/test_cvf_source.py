from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.sources.cvf import CVFSource


def test_cvf_source_is_explicit_placeholder():
    source = CVFSource()

    try:
        source.fetch()
    except NotImplementedError as exc:
        assert "CVF" in str(exc)
    else:
        raise AssertionError("expected CVFSource.fetch() to raise NotImplementedError")
