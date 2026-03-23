from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.schemas import PaperRecord
from app.utils.hashers import build_dedup_key, normalize_title


def test_normalize_title_strips_case_and_punctuation():
    assert normalize_title("Segment Anything: A Foundation Model!") == "segment anything a foundation model"


def test_build_dedup_key_is_stable_for_same_title():
    a = build_dedup_key("Segment Anything", first_author="Kirillov", year=2023)
    b = build_dedup_key("segment anything", first_author="Kirillov", year=2023)
    assert a == b


def test_normalize_title_treats_punctuation_as_separator():
    assert normalize_title("A/B testing") == "a b testing"


def test_paper_record_accepts_optional_dedup_key():
    record = PaperRecord(
        source="arxiv",
        source_paper_id="1234.56789",
        dedup_key="segment anything|kirillov|2023",
        title="Segment Anything",
        paper_url="https://example.com/paper",
    )
    assert record.dedup_key == "segment anything|kirillov|2023"
