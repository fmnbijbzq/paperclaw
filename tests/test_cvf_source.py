from pathlib import Path
import sys

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.sources.cvf import CVFSource


def test_cvf_source_parses_papers_from_index_page():
    html = """
    <html><body>
      <dl>
        <dt>
          <a href="content/CVPR2026/papers/Foo_Bar_Method_CVPR_2026_paper.html">paper</a>
          <a href="content/CVPR2026/papers/Foo_Bar_Method_CVPR_2026_paper.pdf">pdf</a>
        </dt>
        <dd>
          <div class="ptitle"><a href="content/CVPR2026/papers/Foo_Bar_Method_CVPR_2026_paper.html">Foo Bar Method</a></div>
        </dd>
      </dl>
    </body></html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    source = CVFSource(
        base_url="https://example.test",
        conferences=["CVPR"],
        year=2026,
        transport=httpx.MockTransport(handler),
    )

    records = source.fetch()

    assert len(records) == 1
    first = records[0]
    assert first.source == "cvf"
    assert first.source_paper_id.startswith("cvpr:")
    assert first.title == "Foo Bar Method"
    assert first.paper_url == "https://example.test/content/CVPR2026/papers/Foo_Bar_Method_CVPR_2026_paper.html"
    assert first.pdf_url == "https://example.test/content/CVPR2026/papers/Foo_Bar_Method_CVPR_2026_paper.pdf"
    assert first.venue == "CVPR 2026"
    assert first.categories == ["CVPR"]


def test_cvf_source_respects_max_results_across_conferences():
    html = """
    <html><body>
      <dl>
        <dd>
          <div class="ptitle"><a href="content/CVPR2026/papers/Paper_One.html">Paper One</a></div>
        </dd>
        <dd>
          <div class="ptitle"><a href="content/CVPR2026/papers/Paper_Two.html">Paper Two</a></div>
        </dd>
      </dl>
    </body></html>
    """

    call_count = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["value"] += 1
        return httpx.Response(200, text=html)

    source = CVFSource(
        base_url="https://example.test",
        conferences=["CVPR", "ICCV"],
        year=2026,
        max_results=1,
        transport=httpx.MockTransport(handler),
    )

    records = source.fetch()

    assert len(records) == 1
    assert call_count["value"] == 1


def test_cvf_source_skips_unavailable_conference_pages():
    html = """
    <html><body>
      <dl><dd><div class="ptitle"><a href="content/ECCV2026/papers/Eccv_Paper.html">ECCV Paper</a></div></dd></dl>
    </body></html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if "CVPR2026" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, text=html)

    source = CVFSource(
        base_url="https://example.test",
        conferences=["CVPR", "ECCV"],
        year=2026,
        transport=httpx.MockTransport(handler),
    )

    records = source.fetch()

    assert len(records) == 1
    assert records[0].categories == ["ECCV"]
