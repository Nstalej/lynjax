from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str = "Lynjax Backend"
    version: str = "0.5.0-beta"
    environment: str = "beta-test"
    network_policy: str = "simulated-checks-only"


settings = Settings()
