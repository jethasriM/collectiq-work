from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict

class LoginIn(BaseModel):
    email: str
    password: str
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    branch_id: int | None
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
class OutcomeIn(BaseModel):
    event_uuid: str = Field(min_length=8, max_length=64)
    outcome: str
    notes: str = Field(default="", max_length=1000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    occurred_at: datetime
    promise_date: date | None = None
    promise_amount: float | None = Field(default=None, ge=0)
class ReminderIn(BaseModel):
    language: str = "hi"
    template: str = "friendly_due"
class OverrideIn(BaseModel):
    loan_id: int
    new_rank: int = Field(ge=1)
