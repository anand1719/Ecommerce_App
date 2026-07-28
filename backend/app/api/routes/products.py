from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.events import publish_product_event
from app.services.products import create_product, delete_product, get_product, list_products, update_product


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=list[ProductResponse])
def get_products(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return list_products(db, include_inactive=include_inactive)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product_by_id(
    product_id: str,
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProductResponse:
    return get_product(db, product_id, include_inactive=include_inactive)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def add_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ProductResponse:
    product = create_product(db, payload)
    await publish_product_event("product.created", product)
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def edit_product(
    product_id: str,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ProductResponse:
    product = update_product(db, product_id, payload)
    await publish_product_event("product.updated", product)
    return product


@router.delete("/{product_id}", response_model=MessageResponse)
async def remove_product(
    product_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> MessageResponse:
    product = delete_product(db, product_id)
    await publish_product_event("product.deactivated", product)
    return MessageResponse(message="Product deactivated successfully.")
