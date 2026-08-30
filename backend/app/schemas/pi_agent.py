from pydantic import BaseModel, Field


class PiAgentRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=4000)
