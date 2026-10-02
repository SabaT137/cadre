from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    llm_base_url: str
    supervisor_model: str = "glm-5.2"
    supervisor_api_key: str
    worker_model: str = "qwen3.5"
    worker_api_key: str
    worker_native_tools: bool = False
    llm_timeout: int = 120

    devops_database_url: str = "sqlite:///data/devops.db"
    sql_row_limit: int = 200

    templates_dir: Path = ROOT_DIR / "storage" / "templates"
    outputs_dir: Path = ROOT_DIR / "storage" / "outputs"
    checkpoint_db: Path = ROOT_DIR / "data" / "checkpoints.db"
    max_upload_mb: int = 10

    # App database (users, runs, invoices, integrations)
    app_database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'app.db'}"
    app_secret_key: str
    jwt_expiry_hours: int = 12
    admin_username: str = "admin"
    admin_password: str = ""

    # Finance
    finance_config: Path = ROOT_DIR / "config" / "finance.yaml"
    invoice_assets_dir: Path = ROOT_DIR / "storage" / "invoice_assets"

    # Jira
    jira_bootstrap_site: str = ""
    jira_bootstrap_email: str = ""
    jira_bootstrap_api_token: str = ""
    jira_oauth_client_id: str = ""
    jira_oauth_client_secret: str = ""
    jira_oauth_redirect_uri: str = "http://localhost:8000/integrations/jira/callback"
    user_ui_url: str = "http://localhost:8501"

    def resolved_db_url(self) -> str:
        """Make relative sqlite paths relative to the project root."""
        url = self.devops_database_url
        prefix = "sqlite:///"
        if url.startswith(prefix) and not url[len(prefix):].startswith("/"):
            return prefix + str(ROOT_DIR / url[len(prefix):])
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
