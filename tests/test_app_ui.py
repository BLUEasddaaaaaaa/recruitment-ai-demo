from streamlit.testing.v1 import AppTest


def test_app_renders_demo_navigation(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AI_MODE", "fake")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")

    app = AppTest.from_file("src/app.py", default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "招聘数据 AI 自动化 Demo"
    assert any("离线演示模式" in item.value for item in app.warning)
    assert app.radio[0].options == ["简历录入", "候选人流程", "招聘看板"]
