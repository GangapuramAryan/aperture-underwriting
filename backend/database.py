"""Persistence layer.

The schema is designed around one requirement that shapes everything else:
a lending decision must be reconstructable years after it was made.

That is why `DecisionLedger` exists separately from `Decision`. The decision
table holds current state and may be joined, indexed, and read by the console.
The ledger is append-only: it records the exact inputs, model version, feature
hash, thresholds, and reasons at the moment of decision, so that a supervisor
asking "why was this person declined in August 2026" can be answered with
evidence rather than a re-run of today's model against today's data.

Human overrides are recorded in their own table rather than mutating the
decision, because the fact that a human disagreed with the model -- and their
stated justification -- is itself information a model risk reviewer needs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from backend.config import get_settings


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Application(Base):
    """A credit application as submitted."""

    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    external_ref: Mapped[str | None] = mapped_column(String(64), index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    applicant_name: Mapped[str] = mapped_column(String(160))
    requested_amount: Mapped[float] = mapped_column(Float)

    # Full validated feature payload. Retained so a decision can be replayed
    # against the exact inputs that produced it.
    features: Mapped[dict] = mapped_column(JSON)

    is_thin_file: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    decisions: Mapped[list["Decision"]] = relationship(back_populates="application")


class Decision(Base):
    """The outcome of scoring an application."""

    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id"), index=True
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    outcome: Mapped[str] = mapped_column(String(16), index=True)  # APPROVE/REFER/DECLINE
    probability_of_default: Mapped[float] = mapped_column(Float)
    approved_line: Mapped[float | None] = mapped_column(Float)

    fraud_score: Mapped[float] = mapped_column(Float, default=0.0)
    fraud_verdict: Mapped[str] = mapped_column(String(16), default="PASS")

    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    model_version: Mapped[str] = mapped_column(String(64))
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    application: Mapped[Application] = relationship(back_populates="decisions")
    overrides: Mapped[list["Override"]] = relationship(back_populates="decision")


class DecisionLedger(Base):
    """Append-only audit record. Never updated, never deleted.

    `input_hash` and `feature_set_hash` make tampering detectable: if the stored
    inputs are altered, the recorded hash no longer matches them.
    """

    __tablename__ = "decision_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    decision_id: Mapped[str] = mapped_column(String(36), index=True)
    application_id: Mapped[str] = mapped_column(String(36), index=True)

    outcome: Mapped[str] = mapped_column(String(16))
    probability_of_default: Mapped[float] = mapped_column(Float)

    model_version: Mapped[str] = mapped_column(String(64))
    feature_set_hash: Mapped[str] = mapped_column(String(32))
    input_hash: Mapped[str] = mapped_column(String(64))

    approve_threshold: Mapped[float] = mapped_column(Float)
    refer_threshold: Mapped[float] = mapped_column(Float)

    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    shap_attribution: Mapped[dict] = mapped_column(JSON, default=dict)

    # Populated only when an explanation is rendered by a language model, so
    # that generated text can always be traced back to the prompt that made it.
    llm_prompt_hash: Mapped[str | None] = mapped_column(String(64))
    llm_validated: Mapped[bool | None] = mapped_column(Boolean)


class Override(Base):
    """A human underwriter overruling the model, with justification."""

    __tablename__ = "overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    underwriter: Mapped[str] = mapped_column(String(120))
    original_outcome: Mapped[str] = mapped_column(String(16))
    new_outcome: Mapped[str] = mapped_column(String(16))
    justification: Mapped[str] = mapped_column(Text)

    decision: Mapped[Decision] = relationship(back_populates="overrides")


Index("ix_ledger_app_time", DecisionLedger.application_id, DecisionLedger.recorded_at)


# ---------------------------------------------------------------------------
# Engine and session
# ---------------------------------------------------------------------------

_settings = get_settings()

# check_same_thread is a SQLite-only concession for the local dev store; it is
# ignored by Postgres.
_connect_args = (
    {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(_settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create tables if absent. Alembic handles migrations in deployment."""
    Base.metadata.create_all(engine)


def get_session():
    """FastAPI dependency yielding a scoped session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
