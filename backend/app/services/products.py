from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def list_products(db: Session, include_inactive: bool = False) -> list[Product]:
    query = select(Product).order_by(Product.created_at.desc())
    if not include_inactive:
        query = query.where(Product.is_active.is_(True))
    return list(db.scalars(query).all())


def get_product(db: Session, product_id: str, include_inactive: bool = False) -> Product:
    product = db.get(Product, product_id)
    if product is None or (not include_inactive and not product.is_active):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


def create_product(db: Session, payload: ProductCreate) -> Product:
    product = Product(**payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product SKU already exists.") from exc
    db.refresh(product)
    return product


def update_product(db: Session, product_id: str, payload: ProductUpdate) -> Product:
    product = get_product(db, product_id, include_inactive=True)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(product, field, value)

    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product SKU already exists.") from exc
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: str) -> Product:
    product = get_product(db, product_id, include_inactive=True)
    product.is_active = False
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
