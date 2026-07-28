from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.sale import SaleCreate, SaleResponse, SaleStatusUpdate
from app.services.events import publish_sale_event
from app.services.sales import cancel_sale, create_sale, get_sale, list_sales, update_sale_status


router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("", response_model=list[SaleResponse])
def get_sales(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    return list_sales(db, current_user)


@router.get("/{sale_id}", response_model=SaleResponse)
def get_sale_by_id(
    sale_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SaleResponse:
    return get_sale(db, sale_id, current_user)


@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def add_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SaleResponse:
    sale = create_sale(db, current_user, payload)
    await publish_sale_event("sale.created", sale)
    return sale


@router.patch("/{sale_id}/status", response_model=SaleResponse)
async def edit_sale_status(
    sale_id: str,
    payload: SaleStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> SaleResponse:
    sale = update_sale_status(db, sale_id, payload.status)
    await publish_sale_event("sale.status_updated", sale)
    return sale


@router.delete("/{sale_id}", response_model=MessageResponse)
async def remove_sale(
    sale_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    sale = cancel_sale(db, sale_id, current_user)
    await publish_sale_event("sale.cancelled", sale)
    return MessageResponse(message="Sale cancelled successfully.")
