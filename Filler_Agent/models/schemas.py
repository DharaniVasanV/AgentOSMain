from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ProfileFieldCreate(BaseModel):
    field_key: str = Field(..., description="Key name e.g. Full Name")
    field_value: str = Field(..., description="Stored value")
    category: Optional[str] = "General"

class ProfileFieldResponse(BaseModel):
    id: int
    field_key: str
    field_value: str
    category: str

    class Config:
        from_attributes = True

class StartFormRequest(BaseModel):
    form_url: str = Field(..., description="Google Form URL to analyze")

class UpdateMissingInfoRequest(BaseModel):
    answers: Dict[str, str] # question_id -> user answer
    remember_keys: Dict[str, bool] # question_id -> should save to profile

class UpdateReviewRequest(BaseModel):
    fill_mode: str = Field(..., description="auto or manual")
    question_updates: Dict[str, str] # question_id -> edited answer

class ExecutionStep(BaseModel):
    step_name: str
    status: str # pending, running, success, error
    message: str
    timestamp: str
