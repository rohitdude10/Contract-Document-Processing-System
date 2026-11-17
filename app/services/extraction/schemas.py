
from pydantic import BaseModel, Field


class ExtractedFinding(BaseModel):
    variable_name: str = Field(min_length=1)
    extracted_value: str = Field(min_length=1)
