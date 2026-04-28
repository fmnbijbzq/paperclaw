from pathlib import Path
import os
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.storage import Database
from app.schemas import PaperRecord
from app.summarization.schemas import PaperInsightRecord


def _build_paper(source_paper_id: str = "1234.5678", title: str = "Test Paper") -> PaperRecord:
    return PaperRecord(
        source="arxiv",
        source_paper_id=source_paper_id,
        title=title,
        abstract="test abstract",
        full_text="test full text",
        authors=["Alice", "Bob"],
        paper_url=f"https://arxiv.org/abs/{source_paper_id}",
        dedup_key=f"{title.lower()}|alice|2024",
        raw_payload={"id": source_paper_id},
    )


def _seed_paper_with_insight(project_root: Path, db_path: Path, title: str = "Vision Script Paper") -> None:
    db = Database(f"sqlite:///{db_path}")
    db.create_schema()
    paper = db.upsert_paper(_build_paper("5678.1234", title))
    db.upsert_paper_insight(
        paper_id=paper.paper_id,
        insight=PaperInsightRecord(
            summary_short="提出了更稳定的训练与推理策略。",
            summary_long="该论文围绕视觉理解任务提出统一的训练框架。",
            novelty_points=["统一训练范式", "更强鲁棒性", "更低推理成本"],
            limitations=["需要更大规模数据进一步验证"],
            applications=["视觉检索", "视频理解", "内容生产辅助"],
            confidence_score=0.82,
        ),
    )


def _runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    python_path_parts = [str(PROJECT_ROOT)]
    if env.get("PYTHONPATH"):
        python_path_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_path_parts)
    return env


def test_run_content_pipeline_reads_database_url_from_env(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    db_path = project_root / "papers.db"
    env_file = project_root / ".env"
    env_file.write_text(f"DATABASE_URL=sqlite:///{db_path}\n", encoding="utf-8")
    _seed_paper_with_insight(project_root, db_path)

    env = _runtime_env()

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_content_pipeline.py"),
            "--limit",
            "1",
            "--base-dir",
            str(project_root),
        ],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "generated=3" in result.stdout
    generated_paths = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip().endswith('.md')]
    assert len(generated_paths) == 3
    assert all(path.exists() for path in generated_paths)
    assert all("outputs/editorial/" in path.as_posix() for path in generated_paths)

    db = Database(f"sqlite:///{db_path}")
    drafts = db.list_editorial_drafts()
    assert len(drafts) == 3
    assert {draft.platform for draft in drafts} == {"bilibili", "xiaohongshu", "douyin"}


def test_run_content_pipeline_and_export_for_publish_share_runtime_root(tmp_path):
    project_root = tmp_path / "runtime"
    project_root.mkdir()
    db_path = project_root / "papers.db"
    env_file = project_root / ".env"
    env_file.write_text(f"DATABASE_URL=sqlite:///{db_path}\n", encoding="utf-8")
    _seed_paper_with_insight(project_root, db_path, title="Pipeline Export Paper")

    env = _runtime_env()

    generate = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_content_pipeline.py"),
            "--limit",
            "1",
            "--base-dir",
            str(project_root),
        ],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert generate.returncode == 0, generate.stderr

    generated_paths = [Path(line.strip()) for line in generate.stdout.splitlines() if line.strip().endswith('.md')]
    assert generated_paths
    generated_date = generated_paths[0].parent.name

    db = Database(f"sqlite:///{db_path}")
    for draft in db.list_editorial_drafts(platform="bilibili"):
        db.review_editorial_draft(draft.draft_id, actor="reviewer")
        db.approve_editorial_draft(draft.draft_id, actor="reviewer")

    export = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "export_for_publish.py"),
            "--date",
            generated_date,
            "--platform",
            "bilibili",
            "--base-dir",
            str(project_root),
        ],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert export.returncode == 0, export.stderr
    exported = list((project_root / "outputs" / "exported").rglob("bilibili-*.md"))
    assert len(exported) == 1


def test_run_content_pipeline_rejects_non_positive_limit(tmp_path):
    env = _runtime_env()

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_content_pipeline.py"),
            "--limit",
            "0",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "positive integer" in result.stderr


def test_export_for_publish_supports_platform_filter(tmp_path):
    db_path = tmp_path / "papers.db"
    (tmp_path / ".env").write_text(f"DATABASE_URL=sqlite:///{db_path}\n", encoding="utf-8")
    editorial_root = tmp_path / "outputs" / "editorial" / "2026-04-27"
    editorial_root.mkdir(parents=True)
    draft_path = editorial_root / "bilibili-demo.md"
    draft_path.write_text("# demo\n", encoding="utf-8")

    db = Database(f"sqlite:///{db_path}")
    db.create_schema()
    paper = db.upsert_paper(_build_paper("demo-export", "Demo Export Paper"))
    draft = db.upsert_editorial_draft(
        paper_id=paper.paper_id,
        platform="bilibili",
        title="Demo Export Paper",
        hook="Demo Hook",
        markdown_content="# demo\n",
        output_path=str(draft_path),
    )
    db.review_editorial_draft(draft.draft_id, actor="reviewer")
    db.approve_editorial_draft(draft.draft_id, actor="reviewer")

    env = _runtime_env()

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "export_for_publish.py"),
            "--date",
            "2026-04-27",
            "--platform",
            "bilibili",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "exported=1" in result.stdout
    exported = tmp_path / "outputs" / "exported" / "2026-04-27" / "bilibili-demo.md"
    assert exported.exists()
    assert exported.read_text(encoding="utf-8") == "# demo\n"


def test_export_for_publish_returns_error_for_missing_platform_dir(tmp_path):
    db_path = tmp_path / "papers.db"
    (tmp_path / ".env").write_text(f"DATABASE_URL=sqlite:///{db_path}\n", encoding="utf-8")
    (tmp_path / "outputs" / "editorial" / "2026-04-27").mkdir(parents=True)

    env = _runtime_env()

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "export_for_publish.py"),
            "--date",
            "2026-04-27",
            "--platform",
            "douyin",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "no platform drafts" in result.stdout


def test_export_for_publish_rejects_unapproved_drafts(tmp_path):
    db_path = tmp_path / "papers.db"
    (tmp_path / ".env").write_text(f"DATABASE_URL=sqlite:///{db_path}\n", encoding="utf-8")
    editorial_root = tmp_path / "outputs" / "editorial" / "2026-04-27"
    editorial_root.mkdir(parents=True)
    draft_path = editorial_root / "bilibili-demo.md"
    draft_path.write_text("# demo\n", encoding="utf-8")

    db = Database(f"sqlite:///{db_path}")
    db.create_schema()
    paper = db.upsert_paper(_build_paper("demo-reject", "Demo Reject Paper"))
    db.upsert_editorial_draft(
        paper_id=paper.paper_id,
        platform="bilibili",
        title="Demo Reject Paper",
        hook="Demo Hook",
        markdown_content="# demo\n",
        output_path=str(draft_path),
    )

    env = _runtime_env()

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "export_for_publish.py"),
            "--date",
            "2026-04-27",
            "--platform",
            "bilibili",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "approved" in result.stdout


def test_export_for_publish_rejects_unknown_platform(tmp_path):
    env = _runtime_env()

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "export_for_publish.py"),
            "--date",
            "2026-04-27",
            "--platform",
            "../../etc",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "invalid choice" in result.stderr
