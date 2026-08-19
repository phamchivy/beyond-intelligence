"""Unit tests for lib.settings -- no container, no network."""

from lib.settings import Settings


def test_layer_urls_derive_from_storage_url() -> None:
    """Every Delta layer URL is derived from the one storage URL, not typed separately."""
    s = Settings(storage={"url": "s3://my-bucket"})
    assert s.storage.landing_url == "s3://my-bucket/landing"
    assert s.storage.bronze_url == "s3://my-bucket/bronze"
    assert s.storage.silver_url == "s3://my-bucket/silver"
    assert s.storage.gold_url == "s3://my-bucket/gold"
    assert s.storage.quarantine_url == "s3://my-bucket/quarantine"


def test_storage_options_contains_credentials() -> None:
    """storage_options carries the keys delta-rs needs on every call."""
    s = Settings()
    options = s.storage.storage_options
    assert options["AWS_ACCESS_KEY_ID"] == s.storage.access_key
    assert options["AWS_SECRET_ACCESS_KEY"] == s.storage.secret_key
    assert options["AWS_ENDPOINT_URL"] == s.storage.endpoint_url


def test_top_k_is_clamped_by_max_top_k() -> None:
    """max_top_k must not be smaller than the default top_k."""
    s = Settings()
    assert s.retrieval.max_top_k >= s.retrieval.top_k
