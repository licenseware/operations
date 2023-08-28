import pydantic
import pydantic_settings


class AppConfig(pydantic_settings.BaseSettings):
    VERIFY_MAIL_API_KEY: str
    VERIFY_MAIL_URL: str = "https://verifymail.io/api/{email}?key={api_key}"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    TRACING_SERVICE_NAME: str = "email-validator"
    LOG_LEVEL: str = "INFO"

    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    HTTP_TIMEOUT: float = 3.0
    BACKOFF_MAX_TIME: float = 8.0

    LRU_CACHE_SIZE: int = 256

    @pydantic.validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        v = v.upper()

        if v not in ["INFO", "DEBUG", "ERROR"]:
            raise ValueError("LOG_LEVEL must be one of INFO, DEBUG, ERROR")
        return v


conf = AppConfig()
