from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database settings
    database_url: str = ""

    # Application settings
    app_name: str = "AUDIT API"
    debug: bool = False
    port: int = 8000
    # Auth / JWT settings (configure via .env)
    client_id: str | None = None
    tenant_id: str | None = None
    openid_config_url: str | None = None
    valid_audience: str | None = None
    valid_issuer: str | None = None
    timezone: str = "Asia/Kolkata"

    class Config:
        env_file = ".env"


settings = Settings()
