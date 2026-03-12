"""Smoke tests to verify all modules can be imported."""


def test_import_core():
    from enrichrag.core import (
        GeneEnricher,
        KnowledgeGraph,
        PubMedFetcher,
        RelationExtractor,
        WebSearcher,
    )

    assert GeneEnricher is not None
    assert KnowledgeGraph is not None
    assert PubMedFetcher is not None
    assert RelationExtractor is not None
    assert WebSearcher is not None


def test_import_settings():
    from enrichrag.settings import Settings, settings

    assert settings is not None
    assert isinstance(settings, Settings)


def test_import_logging():
    from enrichrag.logging import logger, setup_logging

    assert logger is not None
    assert callable(setup_logging)


def test_import_cli():
    from enrichrag.cli import app

    assert app is not None
