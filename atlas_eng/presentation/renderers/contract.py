from pydantic import BaseModel, ConfigDict


class RenderContract(BaseModel):
    model_config = ConfigDict(frozen=True)
    language: str = "en"
    verbose: bool = False
    deterministic: bool = True
    include_titles: bool = True
    schema_version: str = "1"
