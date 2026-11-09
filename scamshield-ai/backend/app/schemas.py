from pydantic import BaseModel, EmailStr, Field
from typing import Literal

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ScanMessageIn(BaseModel):
    text: str = Field(min_length=3, max_length=12000)

class ScanUrlIn(BaseModel):
    url: str = Field(min_length=8, max_length=2048)

class ScanEmailIn(BaseModel):
    subject: str = Field(default="", max_length=500)
    sender: str = Field(default="", max_length=320)
    reply_to: str = Field(default="", max_length=320)
    body: str = Field(min_length=3, max_length=20000)
    attachment_names: list[str] = Field(default_factory=list, max_length=20)

class BatchIn(BaseModel):
    messages: list[str] = Field(min_length=1, max_length=50)

class FeedbackIn(BaseModel):
    verdict: Literal["correct", "incorrect", "unsure"]
    comment: str | None = Field(default=None, max_length=1000)

class ReportIn(BaseModel):
    category: str = Field(min_length=2, max_length=40)
    description: str = Field(min_length=10, max_length=5000)

class StatusIn(BaseModel):
    status: Literal["submitted", "reviewing", "resolved", "rejected"]
