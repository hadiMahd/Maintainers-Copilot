"""Dataset pipeline settings."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatasetSettings(BaseSettings):
    """Settings for the dataset pipeline."""

    repo_owner: str
    repo_name: str
    max_issues: int = 1000
    github_token: SecretStr | None = None
    raw_issues_path: str = "data/raw/issues.jsonl"
    processed_issues_path: str = "data/processed/issues_labeled.jsonl"
    splits_dir: str = "data/processed/splits"
    report_path: str = "data/processed/dataset_report.json"
    label_mapping_path: str = "config/label_mapping.yml"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
