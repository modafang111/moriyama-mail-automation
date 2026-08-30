from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

from moriyama_mail.intake.request import MyAspPlan
from moriyama_mail.paths import data_dir, default_install_dir, repo_root, secrets_dir


def load_mail_signature() -> str:
    text = (os.getenv("MAIL_SIGNATURE") or "").strip()
    if text:
        return text.replace("\\n", "\n")
    raw = (os.getenv("MAIL_SIGNATURE_FILE") or "").strip()
    path = Path(raw) if raw else repo_root() / "web" / "wordpress-form" / "signature.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


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


@dataclass(frozen=True)
class Settings:
    install_dir: Path
    data_dir: Path
    secrets_dir: Path
    operator_name: str
    test_recipients: tuple[str, ...]
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
    wordpress_form_url: str = ""
    wordpress_intake_token: str = ""
    production_is_immediate: bool = False
    intake_host: str = "127.0.0.1"
    intake_port: int = 8787
    mail_signature: str = ""

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


def _env_file_candidates() -> tuple[Path, ...]:
    install = Path(os.getenv("MORIYAMA_INSTALL_DIR") or default_install_dir())
    candidates = [install / ".env", Path.cwd() / ".env"]
    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(repo_root / ".env")
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return tuple(unique)


def load_settings(env_path: Path | None = None) -> Settings:
    if env_path:
        load_dotenv(env_path, override=False)
    else:
        for candidate in _env_file_candidates():
            if candidate.is_file():
                load_dotenv(candidate, override=False)
                break

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
        wordpress_form_url=(os.getenv("WORDPRESS_FORM_URL") or "").strip()
        or "https://wordpress-123.com/mail-request/",
        wordpress_intake_token=os.getenv("WORDPRESS_INTAKE_TOKEN", "").strip(),
        production_is_immediate=False,
        intake_host=os.getenv("INTAKE_HOST", "").strip() or "127.0.0.1",
        intake_port=int(os.getenv("INTAKE_PORT") or "8787"),
        mail_signature=load_mail_signature(),
    )
