from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class RootResponse(BaseModel):
    message: str
    version: str
    status: str


class Error(BaseModel):
    message: str
