from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

from moriyama_mail.intake.request import MyAspPlan
from moriyama_mail.paths import data_dir, default_install_dir, secrets_dir


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _split_emails(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    items = []
    seen: set[str] = set()
    for part in raw.replace(";", ",").split(","):
        email = part.strip()
        if email and email.lower() not in seen:
            seen.add(email.lower())
            items.append(email)
    return tuple(items)


def _merge_notify(*groups: str) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for email in _split_emails(group):
            key = email.lower()
            if key not in seen:
                seen.add(key)
                merged.append(email)
    return tuple(merged)


@dataclass(frozen=True)
class Settings:
    install_dir: Path
    data_dir: Path
    secrets_dir: Path
    operator_name: str
    test_recipients: tuple[str, ...]
    notify_enabled: bool
    notify_to: tuple[str, ...]
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_use_tls: bool
    google_drive_mode: str
    google_oauth_client_json: Path | None
    google_token_json: Path | None
    google_drive_folder_id: str
    drive_link_label: str
    myasp_mode: str
    myasp_login_url: str
    myasp_user: str
    myasp_password: str
    myasp_api_key: str
    myasp_server_url: str
    myasp_mcp_url: str
    myasp_plans: tuple[MyAspPlan, ...]
    production_is_immediate: bool = False
    intake_host: str = "127.0.0.1"
    intake_port: int = 8787

    @property
    def smtp_ready(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)

    @property
    def drive_live(self) -> bool:
        return self.google_drive_mode == "live" and self.google_oauth_client_json is not None

    @property
    def myasp_live(self) -> bool:
        return self.myasp_mode == "live"

    def plan_by_key(self, key: str) -> MyAspPlan | None:
        for plan in self.myasp_plans:
            if plan.key == key:
                return plan
        return None


def load_settings(env_path: Path | None = None) -> Settings:
    if env_path:
        load_dotenv(env_path, override=False)
    else:
        load_dotenv(override=False)

    install = Path(os.getenv("MORIYAMA_INSTALL_DIR") or default_install_dir())
    base_data = data_dir()
    base_secrets = secrets_dir()

    client_raw = os.getenv("GOOGLE_OAUTH_CLIENT_JSON", "").strip()
    token_raw = os.getenv("GOOGLE_TOKEN_JSON", "").strip()
    client_path = Path(client_raw) if client_raw else None
    token_path = Path(token_raw) if token_raw else base_secrets / "google_token.json"

    return Settings(
        install_dir=install,
        data_dir=base_data,
        secrets_dir=base_secrets,
        operator_name=os.getenv("OPERATOR_NAME", "").strip() or "未設定",
        test_recipients=_split_emails(os.getenv("TEST_RECIPIENTS")),
        notify_enabled=_as_bool(os.getenv("NOTIFY_ENABLED"), True),
        notify_to=_merge_notify(os.getenv("NOTIFY_TO", ""), os.getenv("NOTIFY_TO_2", "")),
        smtp_host=os.getenv("SMTP_HOST", "").strip(),
        smtp_port=int(os.getenv("SMTP_PORT") or "587"),
        smtp_user=os.getenv("SMTP_USER", "").strip(),
        smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
        smtp_from=os.getenv("SMTP_FROM", "").strip(),
        smtp_use_tls=_as_bool(os.getenv("SMTP_USE_TLS"), True),
        google_drive_mode=(os.getenv("GOOGLE_DRIVE_MODE") or "mock").strip().lower(),
        google_oauth_client_json=client_path,
        google_token_json=token_path,
        google_drive_folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip(),
        drive_link_label=os.getenv("DRIVE_LINK_LABEL", "").strip() or "買取案件紹介",
        myasp_mode=(os.getenv("MYASP_MODE") or "mock").strip().lower(),
        myasp_login_url=os.getenv("MYASP_LOGIN_URL", "").strip(),
        myasp_user=os.getenv("MYASP_USER", "").strip(),
        myasp_password=os.getenv("MYASP_PASSWORD", "").strip(),
        myasp_api_key=os.getenv("MYASP_API_KEY", "").strip(),
        myasp_server_url=os.getenv("MYASP_SERVER_URL", "").strip(),
        myasp_mcp_url=os.getenv("MYASP_MCP_URL", "").strip(),
        myasp_plans=(
            MyAspPlan(
                key="test_plan",
                name=os.getenv("MYASP_PLAN_1_NAME", "").strip() or "テストプラン",
                scenario_id=os.getenv("MYASP_PLAN_1_SCENARIO_ID", "").strip(),
            ),
            MyAspPlan(
                key="production_plan",
                name=os.getenv("MYASP_PLAN_2_NAME", "").strip() or "本番プラン",
                scenario_id=os.getenv("MYASP_PLAN_2_SCENARIO_ID", "").strip(),
            ),
        ),
        production_is_immediate=False,
        intake_host=os.getenv("INTAKE_HOST", "").strip() or "127.0.0.1",
        intake_port=int(os.getenv("INTAKE_PORT") or "8787"),
    )
