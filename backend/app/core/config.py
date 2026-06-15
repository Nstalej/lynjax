from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str = "Lynjax Backend"
    version: str = "1.0.0-rc1"
    environment: str = "beta-test"
    network_policy: str = "simulated-checks-only"


settings = Settings()
