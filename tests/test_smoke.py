def test_app_module_imports() -> None:
    from src.app import APP_TITLE

    assert APP_TITLE == "招聘数据 AI 自动化 Demo"
