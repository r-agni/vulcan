"""
Product Inventory API Routes
Endpoints for managing products and viewing interaction metrics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core.database import (
    get_db, Product, ProductZoneMapping, ProductInteractionEvent,
    ProductEngagementMetrics
)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


# Pydantic Models
class ProductCreate(BaseModel):
    name: str
    category: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None


class ProductZoneMappingCreate(BaseModel):
    product_id: int
    zone_id: int
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    shelf_level: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    category: Optional[str]
    sku: Optional[str]
    price: Optional[float]
    is_active: bool

    class Config:
        from_attributes = True


# Product CRUD Endpoints
@router.post("/products", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Manually create a product"""
    db_product = Product(
        name=product.name,
        category=product.category,
        sku=product.sku,
        description=product.description,
        price=product.price,
        is_active=True
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # Create engagement metrics record
    metrics = ProductEngagementMetrics(product_id=db_product.id)
    db.add(metrics)
    db.commit()

    return db_product


@router.get("/products", response_model=List[ProductResponse])
def get_all_products(
    active_only: bool = True,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all products"""
    query = db.query(Product)

    if active_only:
        query = query.filter(Product.is_active == True)

    if category:
        query = query.filter(Product.category == category)

    return query.all()


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get specific product by ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductCreate,
    db: Session = Depends(get_db)
):
    """Update a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in product_update.dict(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete (deactivate) a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    db.commit()
    return {"message": "Product deactivated successfully"}


# Zone Mapping Endpoints
@router.post("/zone-mappings")
def create_zone_mapping(mapping: ProductZoneMappingCreate, db: Session = Depends(get_db)):
    """Map a product to a zone with position"""
    db_mapping = ProductZoneMapping(
        product_id=mapping.product_id,
        zone_id=mapping.zone_id,
        position_x=mapping.position_x,
        position_y=mapping.position_y,
        shelf_level=mapping.shelf_level
    )
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


@router.get("/products/zone/{zone_id}")
def get_products_in_zone(zone_id: int, db: Session = Depends(get_db)):
    """Get all products in a specific zone"""
    mappings = db.query(ProductZoneMapping).filter(
        ProductZoneMapping.zone_id == zone_id
    ).all()

    products_data = []
    for mapping in mappings:
        product = db.query(Product).filter(
            Product.id == mapping.product_id,
            Product.is_active == True
        ).first()

        if product:
            products_data.append({
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "position": {
                    "x": mapping.position_x,
                    "y": mapping.position_y
                },
                "shelf_level": mapping.shelf_level,
                "stock_status": mapping.stock_status
            })

    return products_data


# Interaction Endpoints
@router.get("/interactions")
def get_product_interactions(
    product_id: Optional[int] = None,
    zone_id: Optional[int] = None,
    interaction_type: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db)
):
    """Get product interaction history"""
    query = db.query(ProductInteractionEvent)

    if product_id:
        query = query.filter(ProductInteractionEvent.product_id == product_id)

    if zone_id:
        query = query.filter(ProductInteractionEvent.zone_id == zone_id)

    if interaction_type:
        query = query.filter(ProductInteractionEvent.interaction_type == interaction_type)

    interactions = query.order_by(
        ProductInteractionEvent.timestamp.desc()
    ).limit(limit).all()

    return [
        {
            "id": i.id,
            "product_id": i.product_id,
            "person_id": i.person_id,
            "tracking_id": i.body_tracking_id,
            "zone_id": i.zone_id,
            "interaction_type": i.interaction_type,
            "duration_seconds": i.duration_seconds,
            "engagement_score": i.engagement_score,
            "timestamp": i.timestamp.isoformat() if i.timestamp else None,
            "outcome": i.outcome
        }
        for i in interactions
    ]


# Metrics Endpoints
@router.get("/metrics/product/{product_id}")
def get_product_metrics(product_id: int, db: Session = Depends(get_db)):
    """Get engagement metrics for a specific product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    metrics = db.query(ProductEngagementMetrics).filter(
        ProductEngagementMetrics.product_id == product_id
    ).first()

    if not metrics:
        # Create default metrics if not exists
        metrics = ProductEngagementMetrics(product_id=product_id)
        db.add(metrics)
        db.commit()
        db.refresh(metrics)

    return {
        "product_id": product_id,
        "product_name": product.name,
        "total_views": metrics.total_views,
        "total_touches": metrics.total_touches,
        "total_pickups": metrics.total_pickups,
        "total_putbacks": metrics.total_putbacks,
        "avg_view_duration": metrics.avg_view_duration,
        "avg_engagement_score": metrics.avg_engagement_score,
        "purchase_intent_score": metrics.purchase_intent_score,
        "estimated_conversions": metrics.estimated_conversions,
        "last_interaction": metrics.last_interaction.isoformat() if metrics.last_interaction else None
    }


@router.get("/metrics/summary")
def get_metrics_summary(db: Session = Depends(get_db)):
    """Get overall product inventory metrics summary"""
    all_metrics = db.query(ProductEngagementMetrics).all()

    total_views = sum(m.total_views for m in all_metrics)
    total_touches = sum(m.total_touches for m in all_metrics)
    total_pickups = sum(m.total_pickups for m in all_metrics)

    # Most viewed products
    most_viewed = sorted(
        [
            (m.product_id, m.total_views, db.query(Product).filter(Product.id == m.product_id).first())
            for m in all_metrics
        ],
        key=lambda x: x[1],
        reverse=True
    )[:5]

    # Most interacted products
    most_interacted = sorted(
        [
            (m.product_id, m.total_touches + m.total_pickups, db.query(Product).filter(Product.id == m.product_id).first())
            for m in all_metrics
        ],
        key=lambda x: x[1],
        reverse=True
    )[:5]

    return {
        "total_products": db.query(Product).filter(Product.is_active == True).count(),
        "total_views": total_views,
        "total_touches": total_touches,
        "total_pickups": total_pickups,
        "most_viewed_products": [
            {"product_id": pid, "product_name": p.name if p else "Unknown", "views": views}
            for pid, views, p in most_viewed if p
        ],
        "most_interacted_products": [
            {"product_id": pid, "product_name": p.name if p else "Unknown", "interactions": interactions}
            for pid, interactions, p in most_interacted if p
        ]
    }


# Trigger product detection
@router.post("/analyze-zone/{zone_id}")
def analyze_zone_for_products(zone_id: int, db: Session = Depends(get_db)):
    """
    Trigger Gemini product detection for a specific zone
    Note: This requires access to the product_detector instance from main.py
    """
    return {
        "message": "Product detection endpoint - requires integration with main app instance",
        "zone_id": zone_id,
        "status": "not_implemented"
    }
