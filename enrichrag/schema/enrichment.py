from dataclasses import dataclass
from typing import List

@dataclass
class EnrichmentTerm:
    term_id: str
    term_name: str
    p_value: float
    adj_p_value: float
    genes: List[str]
    coverage: int
    source: str
 