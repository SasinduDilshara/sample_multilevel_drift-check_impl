"""
Advanced Inventory Management System

This module provides comprehensive inventory management capabilities for supply chain
operations including real-time tracking, automated reordering, demand forecasting,
and multi-location inventory optimization.

Features:
- Real-time inventory tracking across multiple warehouses
- Automated stock replenishment with configurable rules
- ABC analysis for inventory categorization
- Demand forecasting using machine learning
- Lot and serial number tracking for traceability
- Integration with supplier and procurement systems
- Advanced analytics and reporting capabilities

Author: Supply Chain Platform Development Team
Version: 3.2.0
Since: 1.0.0
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid

import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field, validator
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import boto3
from kafka import KafkaProducer
import aiofiles

# Configure logging for comprehensive audit trails
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI application instance
app = FastAPI(title="Inventory Management System", version="3.2.0")

class InventoryStatus(str, Enum):
    """Enumeration of possible inventory item statuses"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"
    QUARANTINED = "quarantined"

class StockMovementType(str, Enum):
    """Types of stock movements for inventory tracking"""
    RECEIPT = "receipt"
    SHIPMENT = "shipment"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    RETURN = "return"
    DAMAGE = "damage"
    EXPIRY = "expiry"

class ReorderRule(BaseModel):
    """Configuration for automated reordering rules"""
    item_id: str
    warehouse_id: str
    reorder_point: int = Field(ge=0, description="Minimum stock level before reordering")
    reorder_quantity: int = Field(ge=1, description="Quantity to order when reordering")
    max_stock_level: int = Field(ge=1, description="Maximum stock level")
    supplier_id: str
    lead_time_days: int = Field(ge=1, le=365, description="Supplier lead time in days")
    safety_stock: int = Field(ge=0, description="Safety stock buffer")
    is_active: bool = True

class InventoryItem(BaseModel):
    """Comprehensive inventory item model with full tracking capabilities"""
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sku: str = Field(..., description="Stock Keeping Unit identifier")
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: str = Field(..., description="Product category")
    unit_of_measure: str = Field(default="EA", description="Unit of measurement")
    unit_cost: float = Field(ge=0, description="Unit cost in base currency")
    standard_cost: float = Field(ge=0, description="Standard cost for accounting")
    weight: Optional[float] = Field(None, ge=0, description="Weight per unit")
    dimensions: Optional[Dict[str, float]] = Field(None, description="Length, width, height")
    status: InventoryStatus = InventoryStatus.ACTIVE
    supplier_info: Dict[str, Any] = Field(default_factory=dict)
    quality_requirements: Dict[str, Any] = Field(default_factory=dict)
    storage_requirements: Dict[str, str] = Field(default_factory=dict)
    shelf_life_days: Optional[int] = Field(None, ge=0)
    is_serialized: bool = Field(default=False, description="Track by serial numbers")
    is_lot_tracked: bool = Field(default=False, description="Track by lot numbers")
    abc_classification: Optional[str] = Field(None, regex="^[ABC]$")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class StockLevel(BaseModel):
    """Current stock levels and location information"""
    item_id: str
    warehouse_id: str
    location_id: str
    quantity_on_hand: int = Field(ge=0, description="Physical inventory count")
    quantity_available: int = Field(ge=0, description="Available for allocation")
    quantity_allocated: int = Field(ge=0, description="Allocated to orders")
    quantity_on_order: int = Field(ge=0, description="Outstanding purchase orders")
    quantity_in_transit: int = Field(ge=0, description="In transit between locations")
    last_counted: Optional[datetime] = Field(None, description="Last physical count date")
    cycle_count_due: Optional[datetime] = Field(None, description="Next cycle count due")
    
    @validator('quantity_available')
    def validate_available_quantity(cls, v, values):
        """Ensure available quantity doesn't exceed on-hand quantity"""
        if 'quantity_on_hand' in values and v > values['quantity_on_hand']:
            raise ValueError('Available quantity cannot exceed on-hand quantity')
        return v

class StockMovement(BaseModel):
    """Record of inventory movements for audit trail"""
    movement_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    item_id: str
    warehouse_id: str
    location_id: str
    movement_type: StockMovementType
    quantity: int = Field(..., description="Quantity moved (positive or negative)")
    unit_cost: Optional[float] = Field(None, ge=0)
    reference_number: Optional[str] = Field(None, description="Related document number")
    lot_number: Optional[str] = Field(None, description="Lot number for tracked items")
    serial_numbers: List[str] = Field(default_factory=list)
    expiry_date: Optional[datetime] = Field(None, description="Expiry date for perishables")
    reason_code: Optional[str] = Field(None, description="Reason for movement")
    notes: Optional[str] = Field(None, max_length=500)
    created_by: str = Field(..., description="User who created the movement")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DemandForecast(BaseModel):
    """Demand forecast results for planning purposes"""
    item_id: str
    warehouse_id: str
    forecast_period: str = Field(..., description="Time period (week, month, quarter)")
    forecast_date: datetime
    predicted_demand: float = Field(ge=0)
    confidence_interval_lower: float = Field(ge=0)
    confidence_interval_upper: float = Field(ge=0)
    forecast_accuracy: Optional[float] = Field(None, ge=0, le=1)
    model_used: str = Field(..., description="Forecasting model used")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

@dataclass
class InventoryAnalytics:
    """Comprehensive inventory analytics and KPI calculations"""
    total_inventory_value: float = 0.0
    total_items: int = 0
    stockout_items: int = 0
    overstock_items: int = 0
    slow_moving_items: int = 0
    fast_moving_items: int = 0
    inventory_turnover: float = 0.0
    carrying_cost_percentage: float = 0.0
    service_level: float = 0.0
    abc_analysis: Dict[str, int] = field(default_factory=dict)
    top_value_items: List[Dict[str, Any]] = field(default_factory=list)

class InventoryManagementService:
    """
    Core inventory management service providing comprehensive inventory
    control, tracking, and optimization capabilities.
    
    This service implements advanced inventory management patterns including:
    - Real-time stock tracking across multiple locations
    - Automated reordering with configurable business rules
    - Demand forecasting using machine learning algorithms
    - ABC analysis for inventory categorization
    - Comprehensive audit trails and reporting
    """

    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        """Initialize inventory service with database and cache connections"""
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.s3_client = boto3.client('s3')
        
        # Configuration parameters
        self.reorder_check_interval = 3600  # Check every hour
        self.forecast_horizon_days = 90
        self.abc_analysis_threshold_a = 0.8  # Top 80% of value
        self.abc_analysis_threshold_b = 0.95  # Next 15% of value

    async def create_inventory_item(self, item: InventoryItem) -> InventoryItem:
        """
        Create a new inventory item with comprehensive validation and
        initialization of tracking systems.
        
        Args:
            item: InventoryItem object with complete item information
            
        Returns:
            InventoryItem: Created item with generated IDs and timestamps
            
        Raises:
            HTTPException: If validation fails or item already exists
        """
        logger.info(f"Creating new inventory item: {item.sku}")
        
        async with self.db_pool.acquire() as conn:
            # Check for duplicate SKU
            existing_item = await conn.fetchrow(
                "SELECT item_id FROM inventory_items WHERE sku = $1", item.sku
            )
            
            if existing_item:
                raise HTTPException(status_code=409, detail=f"Item with SKU {item.sku} already exists")
            
            # Insert new item
            item_data = item.dict()
            await conn.execute("""
                INSERT INTO inventory_items (
                    item_id, sku, name, description, category, unit_of_measure,
                    unit_cost, standard_cost, weight, dimensions, status,
                    supplier_info, quality_requirements, storage_requirements,
                    shelf_life_days, is_serialized, is_lot_tracked, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
            """, 
                item.item_id, item.sku, item.name, item.description, item.category,
                item.unit_of_measure, item.unit_cost, item.standard_cost, item.weight,
                json.dumps(item.dimensions), item.status.value, json.dumps(item.supplier_info),
                json.dumps(item.quality_requirements), json.dumps(item.storage_requirements),
                item.shelf_life_days, item.is_serialized, item.is_lot_tracked,
                item.created_at, item.updated_at
            )
            
            # Initialize stock levels for all active warehouses
            warehouses = await conn.fetch("SELECT warehouse_id FROM warehouses WHERE is_active = true")
            for warehouse in warehouses:
                await self.initialize_stock_level(item.item_id, warehouse['warehouse_id'])
            
            # Cache item for quick access
            await self.redis_client.setex(
                f"item:{item.item_id}", 
                3600, 
                json.dumps(item_data)
            )
            
            # Publish item creation event
            await self.publish_inventory_event("item_created", {
                "item_id": item.item_id,
                "sku": item.sku,
                "name": item.name,
                "category": item.category
            })
            
            logger.info(f"Successfully created inventory item: {item.item_id}")
            return item

    async def update_stock_level(self, item_id: str, warehouse_id: str, 
                               movement: StockMovement) -> StockLevel:
        """
        Update stock levels based on inventory movements with comprehensive
        validation and audit trail creation.
        
        Args:
            item_id: Unique identifier for the inventory item
            warehouse_id: Warehouse where the movement occurred
            movement: StockMovement object with movement details
            
        Returns:
            StockLevel: Updated stock level information
            
        Raises:
            HTTPException: If validation fails or insufficient stock
        """
        logger.info(f"Updating stock for item {item_id} in warehouse {warehouse_id}")
        
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Get current stock level
                current_stock = await conn.fetchrow("""
                    SELECT * FROM stock_levels 
                    WHERE item_id = $1 AND warehouse_id = $2
                """, item_id, warehouse_id)
                
                if not current_stock:
                    raise HTTPException(status_code=404, detail="Stock level not found")
                
                # Calculate new quantities based on movement type
                new_quantity = current_stock['quantity_on_hand']
                new_available = current_stock['quantity_available']
                
                if movement.movement_type in [StockMovementType.RECEIPT, StockMovementType.RETURN]:
                    new_quantity += movement.quantity
                    new_available += movement.quantity
                elif movement.movement_type in [StockMovementType.SHIPMENT, StockMovementType.DAMAGE, 
                                              StockMovementType.EXPIRY]:
                    if new_quantity < movement.quantity:
                        raise HTTPException(status_code=400, detail="Insufficient stock for movement")
                    new_quantity -= movement.quantity
                    new_available = min(new_available, new_quantity)
                elif movement.movement_type == StockMovementType.ADJUSTMENT:
                    new_quantity = movement.quantity
                    new_available = min(new_available, new_quantity)
                
                # Update stock level
                await conn.execute("""
                    UPDATE stock_levels 
                    SET quantity_on_hand = $1, quantity_available = $2, updated_at = $3
                    WHERE item_id = $4 AND warehouse_id = $5
                """, new_quantity, new_available, datetime.utcnow(), item_id, warehouse_id)
                
                # Record the movement
                await conn.execute("""
                    INSERT INTO stock_movements (
                        movement_id, item_id, warehouse_id, location_id, movement_type,
                        quantity, unit_cost, reference_number, lot_number, serial_numbers,
                        expiry_date, reason_code, notes, created_by, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                """, 
                    movement.movement_id, movement.item_id, movement.warehouse_id,
                    movement.location_id, movement.movement_type.value, movement.quantity,
                    movement.unit_cost, movement.reference_number, movement.lot_number,
                    json.dumps(movement.serial_numbers), movement.expiry_date,
                    movement.reason_code, movement.notes, movement.created_by, movement.created_at
                )
                
                # Get updated stock level
                updated_stock = await conn.fetchrow("""
                    SELECT * FROM stock_levels 
                    WHERE item_id = $1 AND warehouse_id = $2
                """, item_id, warehouse_id)
                
                # Check for reorder triggers
                await self.check_reorder_rules(item_id, warehouse_id, new_quantity)
                
                # Invalidate cache
                await self.redis_client.delete(f"stock:{item_id}:{warehouse_id}")
                
                # Publish stock movement event
                await self.publish_inventory_event("stock_updated", {
                    "item_id": item_id,
                    "warehouse_id": warehouse_id,
                    "movement_type": movement.movement_type.value,
                    "quantity": movement.quantity,
                    "new_stock_level": new_quantity
                })
                
                return StockLevel(**updated_stock)

    async def perform_abc_analysis(self, warehouse_id: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Perform ABC analysis to categorize inventory items based on value
        and movement patterns for optimized inventory management.
        
        Args:
            warehouse_id: Optional warehouse filter for analysis
            
        Returns:
            Dict[str, List[str]]: Dictionary with A, B, C categories and item lists
        """
        logger.info(f"Performing ABC analysis for warehouse: {warehouse_id or 'all'}")
        
        async with self.db_pool.acquire() as conn:
            # Get inventory value and movement data
            query = """
                SELECT 
                    i.item_id,
                    i.sku,
                    i.name,
                    i.unit_cost,
                    COALESCE(SUM(sl.quantity_on_hand), 0) as total_quantity,
                    COALESCE(SUM(sl.quantity_on_hand * i.unit_cost), 0) as total_value,
                    COALESCE(
                        (SELECT SUM(ABS(sm.quantity)) 
                         FROM stock_movements sm 
                         WHERE sm.item_id = i.item_id 
                         AND sm.created_at >= NOW() - INTERVAL '12 months'
                         AND sm.movement_type IN ('shipment', 'receipt')
                        ), 0
                    ) as annual_movement
                FROM inventory_items i
                LEFT JOIN stock_levels sl ON i.item_id = sl.item_id
                WHERE i.status = 'active'
            """
            
            if warehouse_id:
                query += " AND sl.warehouse_id = $1"
                results = await conn.fetch(query, warehouse_id)
            else:
                results = await conn.fetch(query)
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame([dict(row) for row in results])
            
            if df.empty:
                return {"A": [], "B": [], "C": []}
            
            # Calculate percentage of total value
            total_value = df['total_value'].sum()
            df['value_percentage'] = df['total_value'] / total_value if total_value > 0 else 0
            
            # Sort by value in descending order
            df = df.sort_values('total_value', ascending=False)
            
            # Calculate cumulative percentage
            df['cumulative_percentage'] = df['value_percentage'].cumsum()
            
            # Classify items
            abc_classification = {
                "A": df[df['cumulative_percentage'] <= self.abc_analysis_threshold_a]['item_id'].tolist(),
                "B": df[(df['cumulative_percentage'] > self.abc_analysis_threshold_a) & 
                       (df['cumulative_percentage'] <= self.abc_analysis_threshold_b)]['item_id'].tolist(),
                "C": df[df['cumulative_percentage'] > self.abc_analysis_threshold_b]['item_id'].tolist()
            }
            
            # Update database with classifications
            for category, item_ids in abc_classification.items():
                if item_ids:
                    await conn.execute("""
                        UPDATE inventory_items 
                        SET abc_classification = $1 
                        WHERE item_id = ANY($2)
                    """, category, item_ids)
            
            # Cache results
            await self.redis_client.setex(
                f"abc_analysis:{warehouse_id or 'global'}", 
                86400,  # 24 hours
                json.dumps(abc_classification)
            )
            
            logger.info(f"ABC analysis completed: A={len(abc_classification['A'])}, "
                       f"B={len(abc_classification['B'])}, C={len(abc_classification['C'])}")
            
            return abc_classification

    async def generate_demand_forecast(self, item_id: str, warehouse_id: str, 
                                     forecast_days: int = 90) -> List[DemandForecast]:
        """
        Generate demand forecasts using machine learning algorithms based on
        historical consumption patterns and seasonal trends.
        
        Args:
            item_id: Unique identifier for the inventory item
            warehouse_id: Warehouse for forecast scope
            forecast_days: Number of days to forecast ahead
            
        Returns:
            List[DemandForecast]: List of forecast objects for different periods
        """
        logger.info(f"Generating demand forecast for item {item_id} in warehouse {warehouse_id}")
        
        async with self.db_pool.acquire() as conn:
            # Get historical consumption data
            historical_data = await conn.fetch("""
                SELECT 
                    DATE_TRUNC('week', created_at) as week,
                    SUM(ABS(quantity)) as consumption
                FROM stock_movements
                WHERE item_id = $1 
                AND warehouse_id = $2
                AND movement_type = 'shipment'
                AND created_at >= NOW() - INTERVAL '2 years'
                GROUP BY DATE_TRUNC('week', created_at)
                ORDER BY week
            """, item_id, warehouse_id)
            
            if len(historical_data) < 4:  # Need at least 4 weeks of data
                logger.warning(f"Insufficient historical data for forecasting item {item_id}")
                return []
            
            # Prepare data for machine learning
            df = pd.DataFrame([dict(row) for row in historical_data])
            df['week'] = pd.to_datetime(df['week'])
            df = df.set_index('week')
            
            # Fill missing weeks with zero consumption
            full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq='W')
            df = df.reindex(full_range, fill_value=0)
            
            # Feature engineering
            df['week_number'] = df.index.isocalendar().week
            df['month'] = df.index.month
            df['quarter'] = df.index.quarter
            df['trend'] = range(len(df))
            
            # Prepare features and target
            features = ['week_number', 'month', 'quarter', 'trend']
            X = df[features].values
            y = df['consumption'].values
            
            # Train multiple models
            models = {
                'linear_regression': LinearRegression(),
                'random_forest': RandomForestRegressor(n_estimators=100, random_state=42)
            }
            
            forecasts = []
            best_model = None
            best_score = -float('inf')
            
            for model_name, model in models.items():
                try:
                    model.fit(X, y)
                    score = model.score(X, y)
                    
                    if score > best_score:
                        best_score = score
                        best_model = (model_name, model)
                        
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")
                    continue
            
            if not best_model:
                logger.error(f"No suitable model found for forecasting item {item_id}")
                return []
            
            model_name, model = best_model
            
            # Generate forecasts
            last_week = df.index.max()
            
            for weeks_ahead in range(1, min(forecast_days // 7, 13)):  # Up to 12 weeks
                forecast_date = last_week + pd.Timedelta(weeks=weeks_ahead)
                
                # Prepare features for prediction
                week_num = forecast_date.isocalendar()[1]
                month = forecast_date.month
                quarter = (month - 1) // 3 + 1
                trend = len(df) + weeks_ahead
                
                X_pred = np.array([[week_num, month, quarter, trend]])
                prediction = model.predict(X_pred)[0]
                
                # Calculate confidence intervals (simplified approach)
                residuals = y - model.predict(X)
                std_error = np.std(residuals)
                confidence_lower = max(0, prediction - 1.96 * std_error)
                confidence_upper = prediction + 1.96 * std_error
                
                forecast = DemandForecast(
                    item_id=item_id,
                    warehouse_id=warehouse_id,
                    forecast_period=f"week_{weeks_ahead}",
                    forecast_date=forecast_date,
                    predicted_demand=max(0, prediction),
                    confidence_interval_lower=confidence_lower,
                    confidence_interval_upper=confidence_upper,
                    forecast_accuracy=best_score,
                    model_used=model_name
                )
                
                forecasts.append(forecast)
                
                # Save forecast to database
                await conn.execute("""
                    INSERT INTO demand_forecasts (
                        item_id, warehouse_id, forecast_period, forecast_date,
                        predicted_demand, confidence_interval_lower, confidence_interval_upper,
                        forecast_accuracy, model_used, generated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (item_id, warehouse_id, forecast_period, forecast_date)
                    DO UPDATE SET
                        predicted_demand = EXCLUDED.predicted_demand,
                        confidence_interval_lower = EXCLUDED.confidence_interval_lower,
                        confidence_interval_upper = EXCLUDED.confidence_interval_upper,
                        forecast_accuracy = EXCLUDED.forecast_accuracy,
                        model_used = EXCLUDED.model_used,
                        generated_at = EXCLUDED.generated_at
                """, 
                    item_id, warehouse_id, forecast.forecast_period, forecast.forecast_date,
                    forecast.predicted_demand, forecast.confidence_interval_lower,
                    forecast.confidence_interval_upper, forecast.forecast_accuracy,
                    forecast.model_used, forecast.generated_at
                )
            
            logger.info(f"Generated {len(forecasts)} demand forecasts for item {item_id}")
            return forecasts

    async def check_reorder_rules(self, item_id: str, warehouse_id: str, current_quantity: int) -> None:
        """
        Check and trigger automated reordering based on configured business rules
        and current stock levels.
        """
        async with self.db_pool.acquire() as conn:
            # Get reorder rules for this item and warehouse
            reorder_rule = await conn.fetchrow("""
                SELECT * FROM reorder_rules 
                WHERE item_id = $1 AND warehouse_id = $2 AND is_active = true
            """, item_id, warehouse_id)
            
            if not reorder_rule:
                return
            
            # Check if reorder point reached
            if current_quantity <= reorder_rule['reorder_point']:
                # Create purchase order request
                await self.create_purchase_order_request({
                    "item_id": item_id,
                    "warehouse_id": warehouse_id,
                    "supplier_id": reorder_rule['supplier_id'],
                    "quantity": reorder_rule['reorder_quantity'],
                    "reason": "automatic_reorder",
                    "current_stock": current_quantity,
                    "reorder_point": reorder_rule['reorder_point']
                })

    async def publish_inventory_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Publish inventory events to Kafka for downstream processing"""
        try:
            event = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": event_data
            }
            
            self.kafka_producer.send('inventory_events', value=event)
            self.kafka_producer.flush()
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")

    async def calculate_inventory_analytics(self, warehouse_id: Optional[str] = None) -> InventoryAnalytics:
        """
        Calculate comprehensive inventory analytics and KPIs for management reporting
        """
        async with self.db_pool.acquire() as conn:
            # Base query with optional warehouse filter
            base_filter = "WHERE i.status = 'active'"
            params = []
            
            if warehouse_id:
                base_filter += " AND sl.warehouse_id = $1"
                params.append(warehouse_id)
            
            # Calculate key metrics
            analytics = InventoryAnalytics()
            
            # Total inventory value and items
            result = await conn.fetchrow(f"""
                SELECT 
                    COUNT(DISTINCT i.item_id) as total_items,
                    COALESCE(SUM(sl.quantity_on_hand * i.unit_cost), 0) as total_value
                FROM inventory_items i
                LEFT JOIN stock_levels sl ON i.item_id = sl.item_id
                {base_filter}
            """, *params)
            
            analytics.total_items = result['total_items']
            analytics.total_inventory_value = float(result['total_value'])
            
            # ABC analysis breakdown
            abc_result = await conn.fetch(f"""
                SELECT abc_classification, COUNT(*) as count
                FROM inventory_items i
                LEFT JOIN stock_levels sl ON i.item_id = sl.item_id
                {base_filter}
                GROUP BY abc_classification
            """, *params)
            
            analytics.abc_analysis = {row['abc_classification'] or 'Unclassified': row['count'] 
                                    for row in abc_result}
            
            return analytics

# FastAPI endpoint definitions

@app.post("/api/v1/inventory/items", response_model=InventoryItem)
async def create_item(item: InventoryItem, service: InventoryManagementService = Depends()):
    """Create a new inventory item with comprehensive validation"""
    return await service.create_inventory_item(item)

@app.post("/api/v1/inventory/movements", response_model=StockLevel)
async def record_stock_movement(
    item_id: str, 
    warehouse_id: str, 
    movement: StockMovement,
    service: InventoryManagementService = Depends()
):
    """Record inventory movement and update stock levels"""
    return await service.update_stock_level(item_id, warehouse_id, movement)

@app.get("/api/v1/inventory/abc-analysis")
async def get_abc_analysis(
    warehouse_id: Optional[str] = None,
    service: InventoryManagementService = Depends()
):
    """Perform ABC analysis for inventory categorization"""
    return await service.perform_abc_analysis(warehouse_id)

@app.get("/api/v1/inventory/forecast/{item_id}")
async def get_demand_forecast(
    item_id: str,
    warehouse_id: str,
    forecast_days: int = 90,
    service: InventoryManagementService = Depends()
):
    """Generate demand forecast for inventory planning"""
    return await service.generate_demand_forecast(item_id, warehouse_id, forecast_days)

@app.get("/api/v1/inventory/analytics", response_model=InventoryAnalytics)
async def get_inventory_analytics(
    warehouse_id: Optional[str] = None,
    service: InventoryManagementService = Depends()
):
    """Get comprehensive inventory analytics and KPIs"""
    return await service.calculate_inventory_analytics(warehouse_id)

# Application startup and database initialization
async def init_database():
    """Initialize database connection pool"""
    return await asyncpg.create_pool(
        host="localhost",
        port=5432,
        user="inventory_user",
        password="secure_password",
        database="supply_chain_db",
        min_size=10,
        max_size=20
    )

async def init_redis():
    """Initialize Redis connection"""
    return await redis.from_url("redis://localhost:6379")

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    app.state.db_pool = await init_database()
    app.state.redis_client = await init_redis()
    logger.info("Inventory Management System started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown"""
    await app.state.db_pool.close()
    await app.state.redis_client.close()
    logger.info("Inventory Management System stopped")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
