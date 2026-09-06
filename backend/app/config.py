from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://ps26092:ps26092@localhost:5432/ps26092"
    offline_mode: bool = False
    ulca_user_id: str = ""
    ulca_api_key: str = ""
    sarvam_api_key: str = ""
    mappls_client_id: str = ""
    mappls_client_secret: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
