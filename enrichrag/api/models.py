"""Pydantic models for API layer."""

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    genes: str = Field(..., description="Comma/space/newline-separated gene symbols")
    disease: str = Field(default="cancer", description="Disease context")
    pval: float = Field(default=0.05, ge=0.0, le=1.0, description="P-value threshold")


class HealthResponse(BaseModel):
    status: str = "ok"
