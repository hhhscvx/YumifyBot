from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    MIN_AVAILABLE_ENERGY: int = 800
    SLEEP_BY_MIN_ENERGY: list[int] = [250, 400]

    RANDOM_TAPS_COUNT: list[int] = [30, 80]
    SLEEP_BETWEEN_TAP: list[int] = [7, 10]

    RELOGIN_DELAY: list[int] = [5, 7]

    USE_PROXY_FROM_FILE: bool = False

    WORKDIR: str = "sessions/"


settings = Settings()
