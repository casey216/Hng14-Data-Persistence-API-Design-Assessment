from pydantic import BaseModel


class Data(BaseModel):
    id: str
    name: str
    gender: str
    gender_probability: float
    sample_size: int
    age: int
    age_group: str
    country_id: str
    country_probability: float
    created_at: str

class ProfileResponse(BaseModel):
    status: str
    data: Data

class ExistingProfileResponse(BaseModel):
    status: str
    message: str
    data: Data


class AllProfileResponse(BaseModel):
    status: str
    count: int
    data: list[Data]


class FilterParams(BaseModel):
    model_config = {"extra": "forbid"}

    gender: str | None = None
    country_id: str | None = None
    age_group: str | None = None
