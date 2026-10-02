"""Isolate tests from real data: temp databases/outputs, known admin, no Jira bootstrap network calls."""
import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="office-tests-"))
os.environ.update({
    "APP_DATABASE_URL": f"sqlite:///{_tmp / 'app.db'}",
    "CHECKPOINT_DB": str(_tmp / "checkpoints.db"),
    "OUTPUTS_DIR": str(_tmp / "outputs"),
    "APP_SECRET_KEY": "test-secret-key-for-unit-tests-only-0123456789",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "admin-pass",
    "JIRA_BOOTSTRAP_SITE": "",
    "JIRA_BOOTSTRAP_EMAIL": "",
    "JIRA_BOOTSTRAP_API_TOKEN": "",
})
