import pytest


class StubConverter:
    def __init__(self):
        self.converted = []

    def convert(self, value: str) -> str:
        self.converted.append(value)
        return "<p>converted</p>"


class StubClient:
    def __init__(self, existing=None):
        self.created = []
        self.updated = []
        self.existing = existing or {}

    def get_page_by_title(self, *, space_key: str, title: str):
        return self.existing.get((space_key, title))

    def create_page(
        self,
        *,
        space_key: str,
        title: str,
        html_storage: str,
        parent_id=None,
        labels=None,
    ):
        self.created.append((space_key, title, html_storage, parent_id, tuple(labels or ())))

    def update_page(self, *, page_id: str, html_storage: str, title: str | None = None):
        self.updated.append((page_id, html_storage, title))


class StubPage:
    def __init__(self, page_id: str, title: str):
        self.id = page_id
        self.title = title
        self.space_key = "DOC"


@pytest.fixture()
def stub_converter():
    return StubConverter()


@pytest.fixture()
def stub_client():
    return StubClient()


@pytest.fixture()
def stub_page():
    return StubPage(page_id="stub", title="Stub Page")
