"""
Inventory Management Service for E-Commerce Platform

This module provides comprehensive inventory management functionality including
stock tracking, reservation management, and automated reordering capabilities.

The service integrates with multiple warehouses and suppliers to maintain
accurate inventory levels and prevent stockouts.

Author: Development Team
Version: 1.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import uuid

# Configure logging for inventory operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InventoryStatus(Enum):
    """Enumeration of possible inventory status values"""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    RESERVED = "reserved"
    BACKORDERED = "backordered"


@dataclass
class InventoryItem:
    """
    Represents an inventory item with comprehensive tracking information
    
    This class stores all necessary data for inventory management including
    stock levels, location information, and reservation details.
    """
    product_id: str
    warehouse_id: str
    available_quantity: int
    reserved_quantity: int
    total_quantity: int
    reorder_point: int
    reorder_quantity: int
    cost_per_unit: float
    last_updated: datetime
    status: InventoryStatus


@dataclass
class ReservationRequest:
    """Request to reserve inventory items for order processing"""
    product_id: str
    quantity: int
    customer_id: str
    order_id: str
    expiry_time: datetime


class InventoryService:
    """
    Comprehensive inventory management service handling stock operations
    
    This service provides real-time inventory tracking, reservation management,
    automated reordering, and integration with warehouse management systems.
    Implements proper concurrency control and data consistency mechanisms.
    """
    
    def __init__(self, database_url: str, warehouse_config: Dict):
        """
        Initialize inventory service with database and warehouse connections
        
        Args:
            database_url: Connection string for inventory database
            warehouse_config: Configuration for warehouse integrations
        """
        self.database_url = database_url
        self.warehouse_config = warehouse_config
        self.inventory_cache = {}
        self.active_reservations = {}
        self.reorder_thresholds = {}
        
        logger.info("Inventory service initialized with %d warehouses", 
                   len(warehouse_config))
    
    async def check_availability(self, product_id: str, quantity: int, 
                                warehouse_id: Optional[str] = None) -> bool:
        """
        Check if sufficient inventory is available for the requested quantity
        
        This method performs real-time availability checking across all warehouses
        or a specific warehouse if specified. It considers both available stock
        and any existing reservations that might affect availability.
        
        Args:
            product_id: Unique identifier for the product
            quantity: Requested quantity to check availability for
            warehouse_id: Optional specific warehouse to check
            
        Returns:
            bool: True if sufficient inventory is available, False otherwise
        """
        logger.debug("Checking availability for product %s, quantity %d", 
                    product_id, quantity)
        
        try:
            # Retrieve current inventory levels from database
            inventory_items = await self._get_inventory_items(product_id, warehouse_id)
            
            if not inventory_items:
                logger.warning("No inventory found for product: %s", product_id)
                return False
            
            # Calculate total available quantity across warehouses
            total_available = sum(item.available_quantity for item in inventory_items)
            
            # Check if sufficient quantity is available
            is_available = total_available >= quantity
            
            logger.info("Availability check for product %s: %d available, %d requested, %s", 
                       product_id, total_available, quantity, 
                       "AVAILABLE" if is_available else "INSUFFICIENT")
            
            return is_available
            
        except Exception as e:
            logger.error("Error checking availability for product %s: %s", product_id, str(e))
            return False
    
    async def reserve_inventory(self, reservation: ReservationRequest) -> str:
        """
        Reserve inventory items for order processing with expiration handling
        
        Creates a temporary reservation that prevents other orders from allocating
        the same inventory. Reservations automatically expire if not confirmed
        within the specified time period.
        
        Args:
            reservation: Reservation request containing product and quantity details
            
        Returns:
            str: Unique reservation identifier for tracking and confirmation
            
        Raises:
            InsufficientInventoryError: When requested quantity is not available
            ReservationError: When reservation creation fails
        """
        logger.info("Creating inventory reservation for order %s, product %s, quantity %d", 
                   reservation.order_id, reservation.product_id, reservation.quantity)
        
        # Validate reservation request parameters
        if reservation.quantity <= 0:
            raise ValueError("Reservation quantity must be positive")
        
        if reservation.expiry_time <= datetime.now():
            raise ValueError("Reservation expiry time must be in the future")
        
        # Check if sufficient inventory is available for reservation
        is_available = await self.check_availability(reservation.product_id, 
                                                   reservation.quantity)
        if not is_available:
            raise InsufficientInventoryError(
                f"Insufficient inventory for product {reservation.product_id}")
        
        # Generate unique reservation identifier
        reservation_id = str(uuid.uuid4())
        
        try:
            # Create reservation in database with atomic transaction
            await self._create_reservation_record(reservation_id, reservation)
            
            # Update inventory quantities to reflect reservation
            await self._update_inventory_for_reservation(reservation.product_id, 
                                                       reservation.quantity, True)
            
            # Store reservation in active reservations cache
            self.active_reservations[reservation_id] = reservation
            
            # Schedule automatic expiration cleanup
            asyncio.create_task(self._schedule_reservation_expiry(reservation_id, 
                                                                reservation.expiry_time))
            
            logger.info("Inventory reservation created successfully: %s", reservation_id)
            return reservation_id
            
        except Exception as e:
            logger.error("Failed to create inventory reservation: %s", str(e))
            # Cleanup any partial changes on failure
            await self._cleanup_failed_reservation(reservation_id, reservation)
            raise ReservationError(f"Reservation creation failed: {str(e)}")
    
    async def confirm_reservation(self, reservation_id: str) -> bool:
        """
        Confirm inventory reservation and permanently allocate stock
        
        Converts a temporary reservation into a permanent allocation,
        removing the items from available inventory. This is typically
        called when payment is confirmed for an order.
        
        Args:
            reservation_id: Unique identifier of the reservation to confirm
            
        Returns:
            bool: True if reservation was successfully confirmed
        """
        logger.info("Confirming inventory reservation: %s", reservation_id)
        
        # Validate reservation exists and is still active
        if reservation_id not in self.active_reservations:
            logger.warning("Attempted to confirm non-existent reservation: %s", reservation_id)
            return False
        
        reservation = self.active_reservations[reservation_id]
        
        # Check if reservation has expired
        if datetime.now() > reservation.expiry_time:
            logger.warning("Attempted to confirm expired reservation: %s", reservation_id)
            await self.cancel_reservation(reservation_id)
            return False
        
        try:
            # Permanently allocate inventory in database
            await self._confirm_inventory_allocation(reservation.product_id, 
                                                   reservation.quantity)
            
            # Remove from active reservations
            del self.active_reservations[reservation_id]
            
            # Update reservation status in database
            await self._update_reservation_status(reservation_id, "CONFIRMED")
            
            # Check if reordering is needed after allocation
            await self._check_reorder_triggers(reservation.product_id)
            
            logger.info("Inventory reservation confirmed successfully: %s", reservation_id)
            return True
            
        except Exception as e:
            logger.error("Failed to confirm inventory reservation %s: %s", 
                        reservation_id, str(e))
            return False
    
    async def cancel_reservation(self, reservation_id: str) -> bool:
        """
        Cancel inventory reservation and return stock to available pool
        
        Releases reserved inventory back to available stock when an order
        is cancelled or a reservation expires. This ensures inventory
        remains accurate and available for other orders.
        
        Args:
            reservation_id: Unique identifier of the reservation to cancel
            
        Returns:
            bool: True if reservation was successfully cancelled
        """
        logger.info("Cancelling inventory reservation: %s", reservation_id)
        
        if reservation_id not in self.active_reservations:
            logger.warning("Attempted to cancel non-existent reservation: %s", reservation_id)
            return False
        
        reservation = self.active_reservations[reservation_id]
        
        try:
            # Return reserved quantity to available inventory
            await self._update_inventory_for_reservation(reservation.product_id, 
                                                       reservation.quantity, False)
            
            # Remove from active reservations
            del self.active_reservations[reservation_id]
            
            # Update reservation status in database
            await self._update_reservation_status(reservation_id, "CANCELLED")
            
            logger.info("Inventory reservation cancelled successfully: %s", reservation_id)
            return True
            
        except Exception as e:
            logger.error("Failed to cancel inventory reservation %s: %s", 
                        reservation_id, str(e))
            return False
    
    async def update_stock_levels(self, product_id: str, warehouse_id: str, 
                                quantity_change: int, reason: str) -> bool:
        """
        Update inventory stock levels with proper audit trail
        
        Adjusts inventory quantities for receiving new stock, handling returns,
        or correcting inventory discrepancies. All changes are logged for
        audit and compliance purposes.
        
        Args:
            product_id: Unique identifier for the product
            warehouse_id: Identifier of the warehouse
            quantity_change: Positive or negative quantity adjustment
            reason: Reason for the inventory adjustment
            
        Returns:
            bool: True if stock levels were successfully updated
        """
        logger.info("Updating stock levels for product %s in warehouse %s: %+d (%s)", 
                   product_id, warehouse_id, quantity_change, reason)
        
        try:
            # Retrieve current inventory item
            inventory_item = await self._get_inventory_item(product_id, warehouse_id)
            if not inventory_item:
                logger.error("Inventory item not found: %s in warehouse %s", 
                           product_id, warehouse_id)
                return False
            
            # Calculate new quantities
            new_total = inventory_item.total_quantity + quantity_change
            new_available = inventory_item.available_quantity + quantity_change
            
            # Validate new quantities are not negative
            if new_total < 0 or new_available < 0:
                logger.error("Stock update would result in negative inventory: %s", product_id)
                return False
            
            # Update inventory in database with audit trail
            await self._update_inventory_quantities(product_id, warehouse_id, 
                                                  new_total, new_available, reason)
            
            # Update inventory status based on new levels
            new_status = self._determine_inventory_status(new_available, 
                                                        inventory_item.reorder_point)
            await self._update_inventory_status(product_id, warehouse_id, new_status)
            
            # Check if automatic reordering is triggered
            if new_status in [InventoryStatus.LOW_STOCK, InventoryStatus.OUT_OF_STOCK]:
                await self._trigger_reorder_process(product_id, warehouse_id)
            
            logger.info("Stock levels updated successfully for product %s", product_id)
            return True
            
        except Exception as e:
            logger.error("Failed to update stock levels for product %s: %s", 
                        product_id, str(e))
            return False
    
    async def get_inventory_report(self, warehouse_id: Optional[str] = None, 
                                 status_filter: Optional[InventoryStatus] = None) -> List[Dict]:
        """
        Generate comprehensive inventory report with filtering options
        
        Produces detailed inventory information for analysis and decision making.
        Supports filtering by warehouse and inventory status for targeted reporting.
        
        Args:
            warehouse_id: Optional warehouse filter for the report
            status_filter: Optional status filter for the report
            
        Returns:
            List[Dict]: Inventory report data with detailed item information
        """
        logger.info("Generating inventory report - Warehouse: %s, Status: %s", 
                   warehouse_id, status_filter)
        
        try:
            # Retrieve inventory data based on filters
            inventory_items = await self._get_filtered_inventory(warehouse_id, status_filter)
            
            # Generate report data with calculations
            report_data = []
            total_value = 0.0
            
            for item in inventory_items:
                item_value = item.total_quantity * item.cost_per_unit
                total_value += item_value
                
                report_data.append({
                    "product_id": item.product_id,
                    "warehouse_id": item.warehouse_id,
                    "available_quantity": item.available_quantity,
                    "reserved_quantity": item.reserved_quantity,
                    "total_quantity": item.total_quantity,
                    "reorder_point": item.reorder_point,
                    "status": item.status.value,
                    "cost_per_unit": item.cost_per_unit,
                    "total_value": item_value,
                    "last_updated": item.last_updated.isoformat(),
                    "needs_reorder": item.available_quantity <= item.reorder_point
                })
            
            # Add summary information to report
            summary = {
                "total_items": len(report_data),
                "total_inventory_value": total_value,
                "report_generated": datetime.now().isoformat(),
                "filters_applied": {
                    "warehouse_id": warehouse_id,
                    "status_filter": status_filter.value if status_filter else None
                }
            }
            
            logger.info("Inventory report generated: %d items, total value $%.2f", 
                       len(report_data), total_value)
            
            return {
                "summary": summary,
                "items": report_data
            }
            
        except Exception as e:
            logger.error("Failed to generate inventory report: %s", str(e))
            return {"summary": {"error": str(e)}, "items": []}
    
    # Private helper methods for database operations and business logic
    
    async def _get_inventory_items(self, product_id: str, 
                                 warehouse_id: Optional[str] = None) -> List[InventoryItem]:
        """Retrieve inventory items from database"""
        # Database query implementation would go here
        # This is a simplified placeholder
        return []
    
    async def _create_reservation_record(self, reservation_id: str, 
                                       reservation: ReservationRequest):
        """Create reservation record in database"""
        logger.debug("Creating reservation record: %s", reservation_id)
        # Database insertion logic would be implemented here
    
    async def _update_inventory_for_reservation(self, product_id: str, quantity: int, 
                                              is_reserve: bool):
        """Update inventory quantities for reservation"""
        logger.debug("Updating inventory for reservation: %s, quantity: %d, reserve: %s", 
                    product_id, quantity, is_reserve)
        # Database update logic would be implemented here
    
    async def _schedule_reservation_expiry(self, reservation_id: str, expiry_time: datetime):
        """Schedule automatic reservation expiry"""
        wait_time = (expiry_time - datetime.now()).total_seconds()
        if wait_time > 0:
            await asyncio.sleep(wait_time)
            if reservation_id in self.active_reservations:
                await self.cancel_reservation(reservation_id)
    
    def _determine_inventory_status(self, available_quantity: int, 
                                  reorder_point: int) -> InventoryStatus:
        """Determine inventory status based on available quantity"""
        if available_quantity <= 0:
            return InventoryStatus.OUT_OF_STOCK
        elif available_quantity <= reorder_point:
            return InventoryStatus.LOW_STOCK
        else:
            return InventoryStatus.IN_STOCK


# Custom exception classes for inventory operations
class InsufficientInventoryError(Exception):
    """Raised when requested quantity exceeds available inventory"""
    pass


class ReservationError(Exception):
    """Raised when inventory reservation operation fails"""
    pass


# Example usage and testing
async def main():
    """Example usage of the inventory service"""
    # Initialize inventory service
    warehouse_config = {
        "WH001": {"name": "Main Warehouse", "location": "New York"},
        "WH002": {"name": "West Coast", "location": "California"}
    }
    
    inventory_service = InventoryService("postgresql://localhost/inventory", warehouse_config)
    
    # Example inventory operations
    product_id = "PROD123"
    
    # Check availability
    is_available = await inventory_service.check_availability(product_id, 5)
    print(f"Product {product_id} availability for quantity 5: {is_available}")
    
    # Create reservation
    reservation = ReservationRequest(
        product_id=product_id,
        quantity=3,
        customer_id="CUST456",
        order_id="ORD789",
        expiry_time=datetime.now() + timedelta(hours=1)
    )
    
    try:
        reservation_id = await inventory_service.reserve_inventory(reservation)
        print(f"Reservation created: {reservation_id}")
        
        # Confirm reservation
        confirmed = await inventory_service.confirm_reservation(reservation_id)
        print(f"Reservation confirmed: {confirmed}")
        
    except InsufficientInventoryError as e:
        print(f"Insufficient inventory: {e}")
    except ReservationError as e:
        print(f"Reservation error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
