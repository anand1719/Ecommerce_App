from collections import Counter
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.models.sale import Sale, SaleItem, SaleStatus
from app.models.user import User, UserRole
from app.schemas.sale import SaleCreate


def list_sales(db: Session, current_user: User) -> list[Sale]:
    query = select(Sale).options(joinedload(Sale.items)).order_by(Sale.created_at.desc())
    if current_user.role != UserRole.ADMIN:
        query = query.where(Sale.customer_id == current_user.id)
    return list(db.scalars(query).unique().all())


def get_sale(db: Session, sale_id: str, current_user: User) -> Sale:
    sale = db.scalar(
        select(Sale)
        .where(Sale.id == sale_id)
        .options(joinedload(Sale.items))
    )
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found.")
    if current_user.role != UserRole.ADMIN and sale.customer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found.")
    return sale


def create_sale(db: Session, current_user: User, payload: SaleCreate) -> Sale:
    quantities = Counter()
    for item in payload.items:
        quantities[item.product_id] += item.quantity

    products = list(db.scalars(select(Product).where(Product.id.in_(quantities.keys()))).all())
    products_by_id = {product.id: product for product in products}

    missing_product_ids = set(quantities.keys()) - set(products_by_id.keys())
    if missing_product_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more products were not found.")

    subtotal = Decimal("0.00")
    sale_items: list[SaleItem] = []

    for product_id, quantity in quantities.items():
        product = products_by_id[product_id]
        if not product.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product {product.sku} is inactive.")
        if product.stock_quantity < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {product.sku}.",
            )

        line_total = product.price * quantity
        subtotal += line_total
        product.stock_quantity -= quantity
        sale_items.append(
            SaleItem(
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
                line_total=line_total,
            )
        )

    total_amount = subtotal + payload.tax_amount - payload.discount_amount
    if total_amount < Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount cannot exceed subtotal plus tax.",
        )

    sale = Sale(
        customer_id=current_user.id,
        subtotal=subtotal,
        tax_amount=payload.tax_amount,
        discount_amount=payload.discount_amount,
        total_amount=total_amount,
        items=sale_items,
    )

    db.add(sale)
    db.commit()
    db.refresh(sale)
    return get_sale(db, sale.id, current_user)


def update_sale_status(db: Session, sale_id: str, status_update: SaleStatus) -> Sale:
    sale = db.scalar(
        select(Sale)
        .where(Sale.id == sale_id)
        .options(joinedload(Sale.items))
    )
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found.")

    if sale.status == status_update:
        return sale

    if sale.status == SaleStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled sales cannot be updated.")

    if status_update == SaleStatus.CANCELLED:
        _restore_sale_stock(db, sale)

    sale.status = status_update
    db.add(sale)
    db.commit()
    return get_sale(db, sale.id, sale.customer)


def cancel_sale(db: Session, sale_id: str, current_user: User) -> Sale:
    sale = get_sale(db, sale_id, current_user)
    if sale.status == SaleStatus.CANCELLED:
        return sale
    if current_user.role != UserRole.ADMIN and sale.status != SaleStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending sales can be cancelled by the customer.",
        )

    _restore_sale_stock(db, sale)
    sale.status = SaleStatus.CANCELLED
    db.add(sale)
    db.commit()
    return get_sale(db, sale.id, current_user)


def _restore_sale_stock(db: Session, sale: Sale) -> None:
    for item in sale.items:
        product = db.get(Product, item.product_id)
        if product is not None:
            product.stock_quantity += item.quantity
            db.add(product)
