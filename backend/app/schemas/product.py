from pydantic import BaseModel, computed_field
from uuid import UUID
from datetime import datetime
from typing import Optional


class InventoryOut(BaseModel):
    """Inventory data nested inside product responses."""

    total_stock: int
    reserved: int
    available: int

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    """Single product response."""

    id: UUID
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price_paise: int
    cost_paise: int
    currency: str = "INR"
    image_url: Optional[str] = None
    tags: Optional[list] = None
    is_active: bool = True
    inventory: Optional[InventoryOut] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def price_display(self) -> str:
        """Human-readable price string, e.g. '₹27.99'."""
        return f"₹{self.price_paise / 100:,.2f}"


class ProductListResponse(BaseModel):
    """Paginated product list response."""

    products: list[ProductOut]
    total: int
