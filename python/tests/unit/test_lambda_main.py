"""Tests for lambda_main module."""


def test_lambda_handler_is_callable():
    """Test that lambda_handler is a callable."""
    from apuntador.lambda_main import lambda_handler

    # Mangum is a callable wrapper
    assert callable(lambda_handler)


def test_lambda_main_imports():
    """Test that lambda_main imports work correctly."""
    # This test ensures the module can be imported without errors
    import apuntador.lambda_main  # noqa: F401

    # If we get here, imports worked
    assert True


def test_lambda_main_has_app():
    """Test that lambda_main module has app object."""
    from apuntador.lambda_main import app

    assert app is not None
    assert hasattr(app, "routes")
