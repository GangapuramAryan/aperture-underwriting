"""Aperture API.

Endpoints are deliberately few and each maps to a real underwriting action:
submit and score an application, review the queue, inspect one decision and its
attribution, override with justification, and read the audit ledger.

OpenAPI documentation is generated from the schemas and served at /docs, which
is what makes the API-first claim inspectable rather than asserted.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import (
    Application,
    Decision,
    DecisionLedger,
    Override,
    get_session,
    init_db,
)
from backend.schemas import (
    ApplicationRequest,
    DecisionResponse,
    LedgerEntry,
    OverrideRequest,
    QueueItem,
    ReasonOut,
)
from backend.scoring import DecisionService

settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Ensure the schema exists before the first request is served."""
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    description=(
        "Real-time, multi-modal credit underwriting with adverse action "
        "reason codes and an append-only decision ledger."
    ),
)

# The console runs on a separate origin during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_service: DecisionService | None = None


def get_service() -> DecisionService:
    """Lazily construct the scoring service so import never fails without a model."""
    global _service
    if _service is None:
        _service = DecisionService()
    return _service


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    """Liveness probe that also reports which model is loaded."""
    try:
        service = get_service()
        return {
            "status": "ok",
            "model_version": service.model_version,
            "data_provenance": service.data_provenance,
        }
    except FileNotFoundError as exc:
        return {"status": "degraded", "detail": str(exc)}


@app.post("/v1/decisions", response_model=DecisionResponse, tags=["decisioning"])
def create_decision(
    payload: ApplicationRequest,
    session: Session = Depends(get_session),
) -> DecisionResponse:
    """Score an application and return the decision with its principal reasons."""
    service = get_service()
    features = payload.feature_payload()
    result = service.decide(features)

    application = Application(
        external_ref=payload.external_ref,
        applicant_name=payload.applicant_name,
        requested_amount=payload.requested_amount,
        features=features,
        is_thin_file=result.is_thin_file,
    )
    session.add(application)
    session.flush()

    reasons_json = [reason.to_dict() for reason in result.reasons]

    decision = Decision(
        application_id=application.id,
        outcome=result.outcome,
        probability_of_default=result.probability_of_default,
        approved_line=result.approved_line,
        fraud_score=result.fraud_score,
        fraud_verdict=result.fraud_verdict,
        reason_codes=reasons_json,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
    )
    session.add(decision)
    session.flush()

    # Written in the same transaction as the decision: a decision that exists
    # without a ledger entry would be an unauditable decision.
    session.add(
        DecisionLedger(
            decision_id=decision.id,
            application_id=application.id,
            outcome=result.outcome,
            probability_of_default=result.probability_of_default,
            model_version=result.model_version,
            feature_set_hash=result.feature_set_hash,
            input_hash=result.input_hash,
            approve_threshold=settings.approve_threshold,
            refer_threshold=settings.refer_threshold,
            reason_codes=reasons_json,
            shap_attribution=result.shap_attribution,
        )
    )
    session.commit()

    return DecisionResponse(
        decision_id=decision.id,
        application_id=application.id,
        outcome=result.outcome,
        probability_of_default=result.probability_of_default,
        approved_line=result.approved_line,
        is_thin_file=result.is_thin_file,
        reasons=[
            ReasonOut(
                code=reason.code,
                statement=reason.statement,
                improvement=reason.improvement,
                feature=reason.feature,
                feature_value=reason.feature_value,
                contribution_share=reason.contribution_share,
            )
            for reason in result.reasons
        ],
        fraud_score=result.fraud_score,
        fraud_verdict=result.fraud_verdict,
        fraud_signals=result.fraud_signals,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        decided_at=decision.decided_at or datetime.now(timezone.utc),
    )


@app.get("/v1/queue", response_model=list[QueueItem], tags=["console"])
def read_queue(
    outcome: str | None = Query(default=None, pattern="^(APPROVE|REFER|DECLINE)$"),
    thin_file_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[QueueItem]:
    """Recent decisions for the underwriter console."""
    statement = (
        select(Decision, Application)
        .join(Application, Decision.application_id == Application.id)
        .order_by(Decision.decided_at.desc())
        .limit(limit)
    )
    if outcome:
        statement = statement.where(Decision.outcome == outcome)
    if thin_file_only:
        statement = statement.where(Application.is_thin_file.is_(True))

    return [
        QueueItem(
            application_id=application.id,
            decision_id=decision.id,
            applicant_name=application.applicant_name,
            requested_amount=application.requested_amount,
            outcome=decision.outcome,
            probability_of_default=decision.probability_of_default,
            is_thin_file=application.is_thin_file,
            fraud_verdict=decision.fraud_verdict,
            decided_at=decision.decided_at,
        )
        for decision, application in session.execute(statement).all()
    ]


@app.get("/v1/decisions/{decision_id}", tags=["console"])
def read_decision(decision_id: str, session: Session = Depends(get_session)) -> dict:
    """One decision with its attribution, reasons, and override history."""
    decision = session.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    application = session.get(Application, decision.application_id)
    ledger = session.scalar(
        select(DecisionLedger).where(DecisionLedger.decision_id == decision_id)
    )
    overrides = session.scalars(
        select(Override).where(Override.decision_id == decision_id)
    ).all()

    return {
        "decision_id": decision.id,
        "application_id": decision.application_id,
        "applicant_name": application.applicant_name if application else None,
        "requested_amount": application.requested_amount if application else None,
        "is_thin_file": application.is_thin_file if application else None,
        "outcome": decision.outcome,
        "probability_of_default": decision.probability_of_default,
        "approved_line": decision.approved_line,
        "fraud_score": decision.fraud_score,
        "fraud_verdict": decision.fraud_verdict,
        "reasons": decision.reason_codes,
        "features": application.features if application else {},
        "shap_attribution": ledger.shap_attribution if ledger else {},
        "model_version": decision.model_version,
        "latency_ms": decision.latency_ms,
        "decided_at": decision.decided_at,
        "overrides": [
            {
                "underwriter": override.underwriter,
                "original_outcome": override.original_outcome,
                "new_outcome": override.new_outcome,
                "justification": override.justification,
                "created_at": override.created_at,
            }
            for override in overrides
        ],
    }


@app.post("/v1/decisions/{decision_id}/override", tags=["console"])
def override_decision(
    decision_id: str,
    payload: OverrideRequest,
    session: Session = Depends(get_session),
) -> dict:
    """Record a human underwriter overruling the model.

    The original outcome is preserved. Overwriting it would erase the fact that
    the model and the human disagreed, which is exactly the signal a model risk
    review is looking for.
    """
    decision = session.get(Decision, decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="decision not found")

    override = Override(
        decision_id=decision_id,
        underwriter=payload.underwriter,
        original_outcome=decision.outcome,
        new_outcome=payload.new_outcome,
        justification=payload.justification,
    )
    session.add(override)

    session.add(
        DecisionLedger(
            decision_id=decision_id,
            application_id=decision.application_id,
            outcome=f"OVERRIDE:{payload.new_outcome}",
            probability_of_default=decision.probability_of_default,
            model_version=decision.model_version,
            feature_set_hash="n/a",
            input_hash=hashlib.sha256(
                json.dumps(payload.model_dump(), sort_keys=True).encode()
            ).hexdigest(),
            approve_threshold=settings.approve_threshold,
            refer_threshold=settings.refer_threshold,
            reason_codes=[{"code": "OVR", "statement": payload.justification}],
        )
    )
    session.commit()

    return {
        "decision_id": decision_id,
        "original_outcome": override.original_outcome,
        "new_outcome": override.new_outcome,
        "recorded": True,
    }


@app.get("/v1/ledger", response_model=list[LedgerEntry], tags=["audit"])
def read_ledger(
    application_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[LedgerEntry]:
    """Append-only audit trail, newest first."""
    statement = (
        select(DecisionLedger).order_by(DecisionLedger.recorded_at.desc()).limit(limit)
    )
    if application_id:
        statement = statement.where(DecisionLedger.application_id == application_id)

    return [
        LedgerEntry(
            recorded_at=entry.recorded_at,
            decision_id=entry.decision_id,
            application_id=entry.application_id,
            outcome=entry.outcome,
            probability_of_default=entry.probability_of_default,
            model_version=entry.model_version,
            feature_set_hash=entry.feature_set_hash,
            input_hash=entry.input_hash,
            approve_threshold=entry.approve_threshold,
            refer_threshold=entry.refer_threshold,
            reason_codes=entry.reason_codes or [],
        )
        for entry in session.scalars(statement).all()
    ]
