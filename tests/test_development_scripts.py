import types
from pathlib import Path
from typing import Optional

import pytest

from scripts import (
    bulk_publish_docs,
    common,
    confluence_publisher,
    interactive_publish,
    push_core_docs,
    test_formatting,
)
from scripts.common import PublishOutcome


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    monkeypatch.chdir(repo_root)
    return repo_root


def test_create_page_title_variants(repo):
    readme = repo / "README.md"
    readme.write_text("content", encoding="utf-8")
    nested = repo / "docs" / "intro-guide.md"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("content", encoding="utf-8")

    assert common.create_page_title(readme, repo_root=repo) == "README"
    assert common.create_page_title(nested, repo_root=repo) == "docs / Intro Guide"


def test_publish_documents_handles_create_and_missing(repo, stub_client, stub_converter):
    mapping_store = common.MappingStore(mapping_file=repo / ".cmt" / "map.json")
    existing = repo / "docs" / "existing.md"
    missing = repo / "docs" / "missing.md"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("hello", encoding="utf-8")

    mapping_store.add_mapping(str(existing), space_key="DOC", title="Existing")
    mapping_store.add_mapping(str(missing), space_key="DOC", title="Missing")

    client = stub_client
    converter = stub_converter

    outcomes = common.publish_documents(
        [existing, missing],
        mapping_store=mapping_store,
        client=client,
        converter=converter,
        dry_run=False,
    )

    assert client.created == [("DOC", "Existing", "<p>converted</p>", None, ())]
    assert outcomes[0].action == "created" and outcomes[0].status == "success"
    assert outcomes[1].status == "skipped" and outcomes[1].detail == "File does not exist"


def test_publish_documents_dry_run(repo, stub_client, stub_converter):
    mapping_store = common.MappingStore(mapping_file=repo / ".cmt" / "map.json")
    target = repo / "docs" / "dry.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("hello", encoding="utf-8")
    mapping_store.add_mapping(str(target), page_id="1234")

    outcomes = common.publish_documents(
        [target],
        mapping_store=mapping_store,
        client=stub_client,
        converter=stub_converter,
        dry_run=True,
    )

    assert outcomes[0].action == "dry-run"
    assert outcomes[0].status == "success"


def test_publish_documents_updates_existing_page(repo, stub_client, stub_converter):
    mapping_store = common.MappingStore(mapping_file=repo / ".cmt" / "map.json")
    target = repo / "docs" / "update.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("hello", encoding="utf-8")
    mapping_store.add_mapping(str(target), page_id="42")

    client = stub_client
    converter = stub_converter

    outcomes = common.publish_documents(
        [target],
        mapping_store=mapping_store,
        client=client,
        converter=converter,
        dry_run=False,
    )

    assert client.updated == [("42", "<p>converted</p>", None)]
    assert outcomes[0].action == "updated"
    assert outcomes[0].status == "success"


def test_publish_documents_requires_mapping(repo, stub_client, stub_converter):
    mapping_store = common.MappingStore(mapping_file=repo / ".cmt" / "map.json")
    target = repo / "docs" / "unmapped.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("hello", encoding="utf-8")

    outcomes = common.publish_documents(
        [target],
        mapping_store=mapping_store,
        client=stub_client,
        converter=stub_converter,
        dry_run=False,
    )

    assert outcomes[0].status == "skipped"
    assert outcomes[0].detail == "No mapping found"


def test_publish_documents_rejects_path_outside_repository(
    repo, tmp_path, stub_client, stub_converter
):
    """Ensure paths outside the repo root are rejected with proper status and detail."""
    mapping_store = common.MappingStore(mapping_file=repo / ".cmt" / "map.json")

    # Create a file outside the repository root
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir(parents=True, exist_ok=True)
    outside_file = outside_dir / "outside.md"
    outside_file.write_text("external content", encoding="utf-8")

    # Add a mapping for the external file (even though it should be rejected)
    mapping_store.add_mapping(str(outside_file), space_key="EXT", title="External")

    outcomes = common.publish_documents(
        [outside_file],
        mapping_store=mapping_store,
        client=stub_client,
        converter=stub_converter,
        dry_run=False,
    )

    assert len(outcomes) == 1
    assert outcomes[0].status == "skipped"
    assert outcomes[0].detail == "Path outside repository"
    assert outcomes[0].path == outside_file
    # Verify no operations were attempted on the client
    assert stub_client.created == []
    assert stub_client.updated == []


def test_default_markdown_paths_returns_repo_relative(repo):
    mapping_store = common.MappingStore(mapping_file=repo / ".cmt" / "map.json")
    target = repo / "docs" / "path.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("text", encoding="utf-8")
    mapping_store.add_mapping(str(target), space_key="DOC", title="Path")

    paths = common.default_markdown_paths(mapping_store)
    assert paths == [target]


def test_bulk_publish_main_with_paths(monkeypatch, tmp_path):
    recorded = {}

    def fake_configure_logging(level):
        recorded["verbosity"] = level

    monkeypatch.setattr(bulk_publish_docs, "configure_logging", fake_configure_logging)

    class StubMappingStore:
        def __init__(self):
            recorded["mapping_store"] = True

    demo_file = tmp_path / "demo.md"
    demo_file.write_text("hi", encoding="utf-8")

    outcomes = [PublishOutcome(path=demo_file, action="created", status="success")]

    def fake_publish(targets, *, mapping_store, dry_run):
        recorded["targets"] = list(targets)
        recorded["dry_run"] = dry_run
        return outcomes

    monkeypatch.setattr(bulk_publish_docs, "MappingStore", StubMappingStore)
    monkeypatch.setattr(bulk_publish_docs, "publish_documents", fake_publish)

    exit_code = bulk_publish_docs.main(["--dry-run", str(demo_file)])

    assert exit_code == 0
    assert recorded["dry_run"] is True
    assert recorded["targets"][0] == demo_file


def test_bulk_publish_main_no_targets(monkeypatch):
    monkeypatch.setattr(bulk_publish_docs, "configure_logging", lambda *_: None)
    monkeypatch.setattr(bulk_publish_docs, "MappingStore", lambda: object())
    monkeypatch.setattr(bulk_publish_docs, "default_markdown_paths", lambda *_: [])
    monkeypatch.setattr(bulk_publish_docs, "publish_documents", lambda *_, **__: [])

    assert bulk_publish_docs.main([]) == 1


def test_bulk_publish_main_propagates_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(bulk_publish_docs, "configure_logging", lambda *_: None)

    class StubMappingStore:
        def __init__(self):
            pass

    demo_file = tmp_path / "fail.md"
    demo_file.write_text("oops", encoding="utf-8")

    failure_outcome = PublishOutcome(path=demo_file, action="created", status="failure")

    monkeypatch.setattr(bulk_publish_docs, "MappingStore", StubMappingStore)
    monkeypatch.setattr(bulk_publish_docs, "publish_documents", lambda *_, **__: [failure_outcome])

    assert bulk_publish_docs.main([str(demo_file)]) == 1


def test_interactive_publish_main_with_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(interactive_publish, "configure_logging", lambda *_: None)

    class StubMappingStore:
        def __init__(self):
            pass

    outcomes = [types.SimpleNamespace(path="demo", action="created", status="success")]
    captured_targets = {}

    def fake_publish(targets, *, mapping_store, dry_run):
        captured_targets["targets"] = list(targets)
        captured_targets["dry_run"] = dry_run
        return outcomes

    monkeypatch.setattr(interactive_publish, "MappingStore", StubMappingStore)
    monkeypatch.setattr(interactive_publish, "publish_documents", fake_publish)

    demo_file = tmp_path / "doc.md"
    demo_file.write_text("data", encoding="utf-8")

    assert interactive_publish.main(["--dry-run", str(demo_file)]) == 0
    assert captured_targets["targets"][0] == demo_file
    assert captured_targets["dry_run"] is True


def test_interactive_publish_no_options(monkeypatch):
    monkeypatch.setattr(interactive_publish, "configure_logging", lambda *_: None)
    monkeypatch.setattr(interactive_publish, "MappingStore", lambda: object())
    monkeypatch.setattr(interactive_publish, "_prepare_options", lambda *_: [])
    monkeypatch.setattr(interactive_publish, "publish_documents", lambda *_, **__: [])

    assert interactive_publish.main([]) == 1


def test_interactive_format_mapping_variants():
    mapping_with_page = {"page_id": "99"}
    mapping_with_space = {"space_key": "DOC", "title": "Demo"}
    assert "page_id=99" in interactive_publish._format_mapping(Path("file.md"), mapping_with_page)
    assert "space=DOC title=Demo" in interactive_publish._format_mapping(
        Path("file.md"), mapping_with_space
    )


def test_interactive_prepare_options_sorted(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    class MappingStub:
        def list_mappings(self):
            return {
                "docs/b.md": {"space_key": "DOC", "title": "B"},
                "docs/a.md": {"space_key": "DOC", "title": "A"},
            }

    monkeypatch.setattr(interactive_publish, "find_repository_root", lambda: repo_root)
    options = interactive_publish._prepare_options(MappingStub())
    assert [path.name for path, _ in options] == ["a.md", "b.md"]


def test_prompt_selection_handles_all(monkeypatch):
    inputs = iter(["a"])
    result = interactive_publish._prompt_selection(3, input_func=lambda _: next(inputs))
    assert result == [1, 2, 3]


def test_interactive_main_prompt_flow(monkeypatch, tmp_path):
    monkeypatch.setattr(interactive_publish, "configure_logging", lambda *_: None)

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    file_path = repo_root / "docs" / "demo.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("data", encoding="utf-8")

    class StubMappingStore:
        def list_mappings(self):
            return {"docs/demo.md": {"space_key": "DOC", "title": "Demo"}}

    outcomes = [types.SimpleNamespace(path=file_path, action="updated", status="success")]
    captured = {}

    def fake_publish(targets, *, mapping_store, dry_run):
        captured["targets"] = list(targets)
        captured["dry_run"] = dry_run
        return outcomes

    monkeypatch.setattr(interactive_publish, "MappingStore", StubMappingStore)
    monkeypatch.setattr(interactive_publish, "publish_documents", fake_publish)
    monkeypatch.setattr(interactive_publish, "_prompt_selection", lambda count: [1])
    monkeypatch.setattr(interactive_publish, "find_repository_root", lambda: repo_root)
    monkeypatch.setattr("builtins.print", lambda *_, **__: None)

    exit_code = interactive_publish.main(["--dry-run"])

    assert exit_code == 0
    assert captured["targets"] == [file_path]
    assert captured["dry_run"] is True


def test_interactive_main_reports_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(interactive_publish, "configure_logging", lambda *_: None)
    monkeypatch.setattr(interactive_publish, "MappingStore", lambda: object())

    file_path = tmp_path / "doc.md"
    file_path.write_text("content", encoding="utf-8")

    outcomes = [types.SimpleNamespace(path=file_path, action="created", status="failure")]
    monkeypatch.setattr(interactive_publish, "publish_documents", lambda *_, **__: outcomes)

    assert interactive_publish.main([str(file_path)]) == 1


def test_test_formatting_main_success(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    input_dir = repo_root / "tests" / "golden_corpus" / "input"
    expected_dir = repo_root / "tests" / "golden_corpus" / "expected"
    input_dir.mkdir(parents=True, exist_ok=True)
    expected_dir.mkdir(parents=True, exist_ok=True)

    source = input_dir / "demo.md"
    source.write_text("# Demo", encoding="utf-8")
    expected = expected_dir / "demo.html"
    expected.write_text("<p>demo</p>", encoding="utf-8")

    class DummyConverter:
        def convert(self, value: str) -> str:
            return "<p>demo</p>"

    monkeypatch.setattr(test_formatting, "configure_logging", lambda *_: None)
    monkeypatch.setattr(test_formatting, "find_repository_root", lambda: repo_root)
    monkeypatch.setattr(test_formatting, "MarkdownToConfluenceConverter", lambda: DummyConverter())

    exit_code = test_formatting.main([])
    assert exit_code == 0


def test_test_formatting_main_reports_diffs(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    input_dir = repo_root / "tests" / "golden_corpus" / "input"
    expected_dir = repo_root / "tests" / "golden_corpus" / "expected"
    input_dir.mkdir(parents=True, exist_ok=True)
    expected_dir.mkdir(parents=True, exist_ok=True)

    source = input_dir / "demo.md"
    source.write_text("# Demo", encoding="utf-8")
    expected = expected_dir / "demo.html"
    expected.write_text("<p>expected</p>", encoding="utf-8")

    class DummyConverter:
        def convert(self, value: str) -> str:
            return "<p>actual</p>"

    logs = []

    def fake_error(message, *args):
        logs.append(message)

    class DummyLogger:
        def info(self, *_, **__):
            pass

        def error(self, message, *args):
            fake_error(message, *args)

    monkeypatch.setattr(test_formatting, "configure_logging", lambda *_: None)
    monkeypatch.setattr(test_formatting, "find_repository_root", lambda: repo_root)
    monkeypatch.setattr(test_formatting, "MarkdownToConfluenceConverter", lambda: DummyConverter())
    monkeypatch.setattr(test_formatting, "LOGGER", DummyLogger())

    exit_code = test_formatting.main([])
    assert exit_code == 1
    assert logs  # ensures an error was recorded


def test_confluence_publisher_find_files_and_dry_run(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "docs").mkdir()
    markdown = repo_root / "docs" / "page.md"
    markdown.write_text("content", encoding="utf-8")
    excluded = repo_root / "htmlcov"
    excluded.mkdir()
    (excluded / "ignore.md").write_text("ignore", encoding="utf-8")

    publisher = confluence_publisher.ConfluencePublisher("https://example", "DOC", "1")
    publisher.repo_root = repo_root
    publisher.client = object()

    files = publisher.find_markdown_files()
    assert files == [markdown]

    monkeypatch.setattr("builtins.print", lambda *_, **__: None)
    success, errors = publisher.publish_files(files, dry_run=True)
    assert success == 1 and errors == 0


class StubConfluenceClient:
    def __init__(self, page_factory=None):
        self.created = []
        self.updated = []
        self.lookup = {}
        self._page_factory = page_factory or (
            lambda page_id, title: types.SimpleNamespace(id=page_id, title=title, space_key="DOC")
        )

    def register_existing(self, title: str, page_id: str):
        self.lookup[title] = self._page_factory(page_id, title)

    def get_page_by_title(self, *, space_key: str, title: str):
        return self.lookup.get(title)

    def update_page(self, *, page_id: str, html_storage: str, title: str):
        self.updated.append((page_id, html_storage, title))

    def create_page(
        self,
        *,
        space_key: str,
        title: str,
        html_storage: str,
        parent_id: str,
        labels: Optional[list[str]] = None,
    ):
        self.created.append((space_key, title, html_storage, parent_id, tuple(labels or [])))


def test_confluence_publisher_publish_files_creates_and_updates(
    tmp_path, monkeypatch, stub_converter, stub_page
):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    docs_dir = repo_root / "docs"
    docs_dir.mkdir()
    new_file = docs_dir / "new.md"
    new_file.write_text("# New", encoding="utf-8")
    existing_file = docs_dir / "existing.md"
    existing_file.write_text("# Existing", encoding="utf-8")

    publisher = confluence_publisher.ConfluencePublisher("https://example", "DOC", "1")
    publisher.repo_root = repo_root
    publisher.converter = stub_converter
    publisher.client = StubConfluenceClient(lambda pid, title: stub_page.__class__(pid, title))

    existing_title = common.create_page_title(existing_file, repo_root=repo_root)
    publisher.client.register_existing(existing_title, "page-1")

    monkeypatch.setattr("builtins.print", lambda *_, **__: None)

    success, errors = publisher.publish_files([new_file, existing_file], dry_run=False)

    assert success == 2 and errors == 0
    assert publisher.client.created[0][1] == common.create_page_title(new_file, repo_root=repo_root)
    assert publisher.client.updated[0][0] == "page-1"


def test_push_core_docs_helpers(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    keep = ["README.md", "docs/conversion-fidelity-testing.md"]
    for rel_path in keep:
        target = repo_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("data", encoding="utf-8")

    monkeypatch.setattr(push_core_docs, "find_repository_root", lambda *_: repo_root)
    monkeypatch.setattr("builtins.print", lambda *_, **__: None)

    paths = push_core_docs.get_core_markdown_files()
    assert repo_root / "README.md" in paths
    assert repo_root / "docs" / "conversion-fidelity-testing.md" in paths

    sample = repo_root / "README.md"
    html = push_core_docs.convert_markdown_to_confluence(sample)
    assert html.strip().startswith("<") and "data" in html


def test_push_core_docs_get_credentials(monkeypatch):
    inputs = iter(["user@example.com"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    monkeypatch.setattr("getpass.getpass", lambda prompt: "token-123")
    monkeypatch.setattr("builtins.print", lambda *_, **__: None)

    email, token = push_core_docs.get_credentials()
    assert email == "user@example.com"
    assert token == "token-123"


def test_push_core_docs_get_credentials_missing_email(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    monkeypatch.setattr("builtins.print", lambda *_, **__: None)

    with pytest.raises(SystemExit):
        push_core_docs.get_credentials()
