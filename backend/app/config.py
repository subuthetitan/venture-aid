from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://ps26092:ps26092@localhost:5432/ps26092"
    offline_mode: bool = False
    ulca_user_id: str = ""
    ulca_api_key: str = ""
    # Bhashini's pipeline config call requires a pipelineId, obtained from the
    # ULCA Pipeline Search call or the ULCA web console. It is account/pipeline
    # specific, so it is configured rather than hardcoded.
    ulca_pipeline_id: str = ""
    sarvam_api_key: str = ""
    # MVP_BUILD_PLAN.md: "Bhashini primary, Sarvam fallback, 6s timeout."
    transcription_timeout_seconds: float = 6.0
    mappls_client_id: str = ""
    mappls_client_secret: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
