from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: str = "mongodb://root:root@localhost:27017/?authSource=admin"
    mongodb_db: str = "sts"


settings = Settings()
