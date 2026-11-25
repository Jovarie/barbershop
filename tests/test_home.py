"""The home page loads (uses the shared fixtures, so no real database is touched)."""


def test_home_page_loads(client):
    assert client.get("/").status_code == 200
