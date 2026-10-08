from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: str = "mongodb://root:root@localhost:27017/?authSource=admin"
    mongodb_db: str = "sts"

    jwt_access_secret: str
    jwt_refresh_secret: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    seed_email_pattern: str
    seed_password: str

    @field_validator("seed_email_pattern")
    @classmethod
    def _pattern_has_placeholder(cls, value: str) -> str:
        if "{n}" not in value:
            raise ValueError("SEED_EMAIL_PATTERN must contain '{n}', e.g. user{n}@sts.com")
        return value


settings = Settings()
