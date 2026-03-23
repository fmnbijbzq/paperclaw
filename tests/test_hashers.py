from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.utils.hashers import build_dedup_key, normalize_title


def test_normalize_title_strips_case_and_punctuation():
    assert normalize_title("Segment Anything: A Foundation Model!") == "segment anything a foundation model"


def test_build_dedup_key_is_stable_for_same_title():
    a = build_dedup_key("Segment Anything", first_author="Kirillov", year=2023)
    b = build_dedup_key("segment anything", first_author="Kirillov", year=2023)
    assert a == b
