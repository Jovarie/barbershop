"""Tests for the public pages."""
from app import create_app


def test_home_page_loads():
    """The home page returns HTTP 200."""
    client = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}).test_client()
    assert client.get("/").status_code == 200
