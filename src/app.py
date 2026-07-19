from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from src.ai import create_ai_provider
from src.config import Settings
from src.db.repository import Repository
from src.services.intake import IntakeService
from src.ui.dashboard_page import render_dashboard_page
from src.ui.intake_page import render_intake_page
from src.ui.pipeline_page import render_pipeline_page

APP_TITLE = "招聘数据 AI 自动化 Demo"
ROOT = Path(__file__).resolve().parents[1]


@st.cache_resource
def get_settings() -> Settings:
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'demo.db'}")
    settings = Settings()
    if settings.database_url.startswith("sqlite:///"):
        Path(settings.database_url.removeprefix("sqlite:///")).expanduser().parent.mkdir(
            parents=True, exist_ok=True
        )
    return settings


@st.cache_resource
def get_repository(database_url: str) -> Repository:
    return Repository(database_url)


@st.cache_resource
def get_provider(settings: Settings):
    return create_ai_provider(settings)


@st.cache_resource
def get_intake_service(database_url: str, settings: Settings) -> IntakeService:
    return IntakeService(get_repository(database_url), get_provider(settings))


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🧭", layout="wide")
    settings = get_settings()
    repository = get_repository(settings.database_url)
    intake_service = get_intake_service(settings.database_url, settings)

    st.title(APP_TITLE)
    if settings.ai_mode == "fake":
        st.warning("离线演示模式：AI 使用本地确定性模拟，不会调用外部模型。")
    st.info("本地模拟：尚未连接企业微信/腾讯文档")
    st.caption(
        "仅可使用受控、匿名化输入。上传限制见 "
        "[文档解析安全说明](docs/security/document-parsing-limitations.md)。"
    )

    page = st.sidebar.radio("功能", ["简历录入", "候选人流程", "招聘看板"])
    st.sidebar.caption("本地访问：http://localhost:8501")
    if page == "简历录入":
        render_intake_page(intake_service, ROOT / "samples" / "anonymous-resume.txt")
    elif page == "候选人流程":
        render_pipeline_page(repository)
    else:
        render_dashboard_page(repository)


if __name__ == "__main__":
    main()
