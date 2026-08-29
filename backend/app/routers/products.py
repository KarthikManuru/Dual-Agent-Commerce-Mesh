from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.product import Product
from app.models.inventory import Inventory
from app.schemas.product import ProductOut, ProductListResponse, InventoryOut

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    category: str | None = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all products with inventory counts. Optionally filter by category."""
    query = select(Product).options(joinedload(Product.inventory))

    if active_only:
        query = query.where(Product.is_active == True)
    if category:
        query = query.where(Product.category == category)

    query = query.order_by(Product.name)
    result = await db.execute(query)
    products = result.unique().scalars().all()

    # Build response with computed inventory.available
    product_list = []
    for p in products:
        pout = ProductOut.model_validate(p)
        if p.inventory:
            pout.inventory = InventoryOut(
                total_stock=p.inventory.total_stock,
                reserved=p.inventory.reserved,
                available=p.inventory.available,
            )
        product_list.append(pout)

    return ProductListResponse(products=product_list, total=len(product_list))


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single product by ID with inventory."""
    query = (
        select(Product)
        .options(joinedload(Product.inventory))
        .where(Product.id == product_id)
    )
    result = await db.execute(query)
    product = result.unique().scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    pout = ProductOut.model_validate(product)
    if product.inventory:
        pout.inventory = InventoryOut(
            total_stock=product.inventory.total_stock,
            reserved=product.inventory.reserved,
            available=product.inventory.available,
        )
    return pout
