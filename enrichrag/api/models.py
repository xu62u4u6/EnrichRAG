"""Pydantic models for API layer."""

from typing import List

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    genes: str = Field(..., description="Comma/space/newline-separated gene symbols")
    disease: str = Field(default="cancer", description="Disease context")
    pval: float = Field(default=0.05, ge=0.0, le=1.0, description="P-value threshold")


class HealthResponse(BaseModel):
    status: str = "ok"


class ValidateGenesRequest(BaseModel):
    genes: str = Field(..., description="Comma/space/newline-separated gene symbols")


class GeneValidationRow(BaseModel):
    input_gene: str
    normalized_gene: str = ""
    status: str
    source: str = ""
    gene_id: str = ""
    official_name: str = ""
    description: str = ""


class ValidateGenesResponse(BaseModel):
    normalized_genes: List[str]
    accepted: List[GeneValidationRow]
    remapped: List[GeneValidationRow]
    rejected: List[GeneValidationRow]
    rows: List[GeneValidationRow]
    summary: dict


class GeneProfileResponse(BaseModel):
    canonical_symbol: str
    gene_id: str = ""
    official_symbol: str = ""
    official_full_name: str = ""
    synonyms: str = ""
    description: str = ""
    type_of_gene: str = ""
    chromosome: str = ""
    map_location: str = ""
    dbxrefs: str = ""
    modification_date: str = ""
    tax_id: int = 9606


class ChatRequest(BaseModel):
    query: str = Field(..., description="User's question")
    result: dict = Field(default_factory=dict, description="Full pipeline result payload")
    history: List[dict] = Field(default_factory=list, description="Previous chat messages")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=200)
    display_name: str = Field(..., min_length=1, max_length=120)


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str


class HistoryItemResponse(BaseModel):
    id: int
    disease_context: str
    gene_count: int
    input_genes: List[str]
    created_at: str
