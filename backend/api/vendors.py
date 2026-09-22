from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Body, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..services.vendor_service import (
    get_vendor_network_stats,
    escalate_vendor_to_all_authorities,
    get_authority_notices,
    record_authority_action,
)
from ..security import require_roles

router = APIRouter()


class EscalatePayload(BaseModel):
    vendor_name: str = Field(..., description="Name of the suspect contractor/vendor")
    reason: Optional[str] = Field(None, description="Forensic audit reason for flagging")


class AuthorityActionPayload(BaseModel):
    action: str = Field(..., description="Action taken by the authority")
    actor: str = Field(..., description="Email/ID of the authority official")


@router.get("/")
def get_vendors(
    current_user: User = Depends(require_roles("CAG", "COLLECTOR")),
    db: Session = Depends(get_db)
):
    """
    Returns national vendor network and collusion statistics.
    Restricted to CAG auditors and District Collectors.
    """
    return get_vendor_network_stats(db)


@router.post("/escalate", status_code=status.HTTP_201_CREATED)
def trigger_vendor_escalation(
    payload: EscalatePayload,
    db: Session = Depends(get_db)
):
    """
    Instantly dispatches statutory vigilance notices to all 4 authorities
    (Ministry/CAG, SNA, District Collector, GeM/CVC) when a vendor is flagged.
    """
    notices = escalate_vendor_to_all_authorities(
        db=db,
        vendor_name=payload.vendor_name,
        reason=payload.reason
    )
    return {
        "success": True,
        "vendor": payload.vendor_name,
        "dispatched_count": len(notices),
        "notices": notices
    }


@router.get("/notices")
def list_authority_notices(
    vendor_name: Optional[str] = Query(None, description="Filter by vendor name"),
    authority_tier: Optional[str] = Query(None, description="Filter by authority tier"),
    db: Session = Depends(get_db)
):
    """
    Retrieves all dispatched authority notices and their enforcement status.
    """
    return get_authority_notices(db=db, vendor_name=vendor_name, authority_tier=authority_tier)


@router.post("/notices/{notice_id}/action")
def log_authority_action(
    notice_id: str,
    payload: AuthorityActionPayload,
    db: Session = Depends(get_db)
):
    """
    Logs an enforcement action taken by an authorized government tier.
    """
    res = record_authority_action(
        db=db,
        notice_id=notice_id,
        action=payload.action,
        actor_email=payload.actor
    )
    return res
