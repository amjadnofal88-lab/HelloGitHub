from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AIG API"
    debug: bool = False
    database_url: str = "sqlite:///./aig.db"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
