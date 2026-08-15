from pydantic import BaseModel, Field


class ReadingSeries(BaseModel):
    consumer_id: str
    dates: list[str] = Field(..., description="ISO date strings, ascending order")
    consumption_kwh: list[float] = Field(..., description="Daily kWh, same length as dates")


class ScoreResponse(BaseModel):
    consumer_id: str
    risk_score: float
    supervised_prob: float
    anomaly_score: float
    flagged: bool
    reasons: list[str]
    note: str | None = None


class ScanResult(BaseModel):
    consumer_id: str
    transformer_id: str
    risk_score: float
    supervised_prob: float
    anomaly_score: float
    reasons: list[str]


class ScanResponse(BaseModel):
    total_consumers: int
    flagged_count: int
    threshold: float
    results: list[ScanResult]
