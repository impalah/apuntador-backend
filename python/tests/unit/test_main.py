"""Tests for main application entry point."""


def test_main_imports():
    """Test that main module can be imported."""
    import apuntador.main  # noqa: F401

    assert True


def test_main_app_exists():
    """Test that main module exports app."""
    from apuntador.main import app

    assert app is not None
    assert hasattr(app, "routes")


def test_main_module_structure():
    """Test main module has expected structure."""
    import apuntador.main as main_module

    # Module should be importable and have key attributes
    assert hasattr(main_module, "app")
    assert main_module.app is not None
