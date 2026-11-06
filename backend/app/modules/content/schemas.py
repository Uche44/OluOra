import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field


OpportunityStatus = Literal["new", "saved", "dismissed"]
CalendarStatus = Literal["idea", "planned", "in_progress", "ready", "published"]


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class OpportunityEvidenceOut(BaseModel):
    id: uuid.UUID
    insight_id: uuid.UUID | None = None
    cluster_id: uuid.UUID | None = None
    comment_id: uuid.UUID | None = None
    quote: str | None = None


class ContentOpportunityOut(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID | None = None
    source_video_id: uuid.UUID | None = None
    source_video_title: str | None = None
    title: str
    rationale: str
    suggested_format: str
    suggested_length: str
    suggested_angle: str
    priority: str
    status: str
    is_evidence_backed: bool
    is_scheduled: bool = False
    scheduled_dates: list[date] = Field(default_factory=list)
    generated_at: datetime
    evidence: list[OpportunityEvidenceOut]


class OpportunityListResponse(BaseModel):
    data: list[ContentOpportunityOut]
    pagination: Pagination


class GenerateOpportunitiesResponse(BaseModel):
    data: list[ContentOpportunityOut]
    cached: bool


class GenerateOpportunitiesRequest(BaseModel):
    analysis_id: uuid.UUID
    limit: int = Field(default=3, ge=1, le=6)
    force: bool = False


class OpportunityStatusUpdate(BaseModel):
    status: OpportunityStatus


class AnalysisSourceOut(BaseModel):
    analysis_id: uuid.UUID
    video_id: uuid.UUID
    video_title: str
    thumbnail_url: str | None = None
    platform: str
    comments_analyzed: int
    created_at: datetime


class AnalysisSourceListResponse(BaseModel):
    data: list[AnalysisSourceOut]


# --- Internal LLM response shapes -------------------------------------------
# The model returns strings for IDs; the service validates them against the
# creator's analysis before anything is persisted.


class LLMEvidence(BaseModel):
    insight_ref: str | None = None
    cluster_ref: str | None = None
    comment_ref: str | None = None
    insight_id: str | None = None
    cluster_id: str | None = None
    comment_id: str | None = None


class LLMOpportunity(BaseModel):
    title: str
    rationale: str = ""
    suggested_format: str = "tutorial"
    suggested_length: str = "long_form"
    suggested_angle: str = ""
    priority: str = "medium"
    evidence: list[LLMEvidence] = Field(default_factory=list)


class LLMOpportunitiesResponse(BaseModel):
    opportunities: list[LLMOpportunity] = Field(default_factory=list)


# --- Weekly calendar ---------------------------------------------------------


class CalendarItemCreate(BaseModel):
    opportunity_id: uuid.UUID | None = None
    title: str | None = None
    angle: str | None = None
    notes: str | None = None
    content_context: str | None = None
    format: str | None = None
    length: str | None = None
    platform: str = "youtube"
    scheduled_date: date
    scheduled_time: time | None = None
    status: CalendarStatus = "idea"


class CalendarItemUpdate(BaseModel):
    title: str | None = None
    angle: str | None = None
    notes: str | None = None
    content_context: str | None = None
    format: str | None = None
    length: str | None = None
    platform: str | None = None
    scheduled_date: date | None = None
    scheduled_time: time | None = None
    status: CalendarStatus | None = None


class CalendarItemOut(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID | None = None
    title: str
    angle: str
    notes: str
    content_context: str
    format: str
    length: str
    platform: str
    scheduled_date: date
    scheduled_time: time | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class CalendarWeekResponse(BaseModel):
    week_start: date
    week_end: date
    data: list[CalendarItemOut]


class CalendarPlanRequest(BaseModel):
    week_start: date
    opportunity_ids: list[uuid.UUID] = Field(min_length=1)
    # 0 = Monday … 6 = Sunday. Defaults to Mon/Wed/Fri.
    days: list[int] = Field(default_factory=lambda: [0, 2, 4])
    platform: str = "youtube"


class CalendarPlanResponse(BaseModel):
    data: list[CalendarItemOut]
    planned: int


# --- Scripts / content briefs -----------------------------------------------


class ScriptSection(BaseModel):
    heading: str = ""
    content: str = ""


class ScriptContent(BaseModel):
    working_title: str = ""
    hook: str = ""
    body: str = ""
    sections: list[ScriptSection] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    cta: str = ""
    caption: str = ""
    description: str = ""
    alt_titles: list[str] = Field(default_factory=list)


class ScriptOut(ScriptContent):
    id: uuid.UUID
    calendar_item_id: uuid.UUID
    version: int
    model: str | None = None
    generated_at: datetime
    user_edited_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ScriptGenerateRequest(BaseModel):
    force: bool = False


class ScriptGenerateResponse(BaseModel):
    data: ScriptOut
    cached: bool


class ScriptUpdate(BaseModel):
    working_title: str | None = None
    hook: str | None = None
    body: str | None = None
    sections: list[ScriptSection] | None = None
    talking_points: list[str] | None = None
    examples: list[str] | None = None
    cta: str | None = None
    caption: str | None = None
    description: str | None = None
    alt_titles: list[str] | None = None


class ScriptListResponse(BaseModel):
    data: list[ScriptOut]


# --- Creator style profile ---------------------------------------------------


class StyleProfileOut(BaseModel):
    tone: str
    language: str
    audience_description: str
    technical_depth: str
    preferred_structures: list[str]
    avoid: list[str]
    posting_cadence: int
    preferred_formats: list[str]
    preferred_platforms: list[str]
    reference_notes: str
    updated_at: datetime | None = None


class StyleProfileUpdate(BaseModel):
    tone: str = ""
    language: str = ""
    audience_description: str = ""
    technical_depth: str = "intermediate"
    preferred_structures: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    posting_cadence: int = Field(default=3, ge=1, le=14)
    preferred_formats: list[str] = Field(default_factory=list)
    preferred_platforms: list[str] = Field(default_factory=lambda: ["youtube"])
    reference_notes: str = ""
