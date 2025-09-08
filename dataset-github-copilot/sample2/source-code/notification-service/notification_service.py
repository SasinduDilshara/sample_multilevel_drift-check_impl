"""
Notification Service for Banking Platform

This service handles all customer communications including transaction alerts,
account notifications, marketing messages, and security alerts. It supports
multiple delivery channels and ensures reliable message delivery.

The service implements async processing with comprehensive retry logic,
rate limiting, and delivery tracking for optimal performance and reliability.

Author: Banking Corp Development Team
Version: 1.5.0
Since: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from kafka import KafkaProducer
import sendgrid
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Banking Notification Service", version="1.5.0")

class NotificationChannel(str, Enum):
    """Enumeration of supported notification delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"

class NotificationPriority(str, Enum):
    """Priority levels for notification processing and delivery"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationStatus(str, Enum):
    """Status tracking for notification lifecycle"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"

class NotificationRequest(BaseModel):
    """Request model for sending notifications"""
    customer_id: str = Field(..., description="Customer identifier")
    channel: NotificationChannel = Field(..., description="Delivery channel")
    template_id: str = Field(..., description="Template identifier")
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL)
    recipient: str = Field(..., description="Recipient address (email/phone/device_id)")
    subject: str = Field(..., description="Notification subject")
    content: str = Field(..., description="Notification content")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = Field(None, description="Schedule for future delivery")

class Notification(BaseModel):
    """Internal notification model with full tracking information"""
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    channel: NotificationChannel
    template_id: str
    priority: NotificationPriority
    subject: str
    content: str
    recipient: str
    status: NotificationStatus = NotificationStatus.PENDING
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CustomerPreferences(BaseModel):
    """Customer notification preferences and settings"""
    customer_id: str
    email_enabled: bool = True
    sms_enabled: bool = True
    push_enabled: bool = True
    marketing_enabled: bool = False
    security_alerts: bool = True
    transaction_alerts: bool = True
    balance_alerts: bool = True
    preferred_channel: NotificationChannel = NotificationChannel.EMAIL
    quiet_hours_start: time = time(22, 0)  # 10 PM
    quiet_hours_end: time = time(8, 0)     # 8 AM
    timezone: str = "UTC"

class NotificationService:
    """
    Core notification service handling all customer communications.
    
    This service manages multiple delivery channels with comprehensive
    error handling, retry logic, and performance optimization through
    async processing and caching.
    """

    def __init__(self):
        """Initialize notification service with external dependencies"""
        # Database connection for notification storage
        self.mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
        self.db = self.mongo_client.banking_notifications
        
        # Redis for caching and rate limiting
        self.redis_client = None
        
        # External service clients
        self.sendgrid_client = sendgrid.SendGridAPIClient(api_key="your_sendgrid_api_key")
        self.twilio_client = Client("your_twilio_sid", "your_twilio_token")
        
        # Kafka producer for async processing
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Rate limiting configuration
        self.rate_limits = {
            NotificationChannel.EMAIL: {"per_minute": 1000, "per_hour": 10000},
            NotificationChannel.SMS: {"per_minute": 10, "per_hour": 100},
            NotificationChannel.PUSH: {"per_minute": 500, "per_hour": 5000}
        }

    async def startup(self):
        """Initialize async components during service startup"""
        self.redis_client = await redis.from_url("redis://localhost:6379")
        logger.info("Notification service started successfully")

    async def send_notification(self, request: NotificationRequest) -> Notification:
        """
        Send a notification through the specified channel with comprehensive
        validation, rate limiting, and error handling.
        
        Args:
            request: The notification request with all delivery details
            
        Returns:
            Notification: The created notification with tracking information
            
        Raises:
            HTTPException: If validation fails or rate limits are exceeded
        """
        logger.info(f"Processing notification request for customer {request.customer_id} "
                   f"via {request.channel}")
        
        # Create notification entity
        notification = Notification(**request.dict())
        
        try:
            # Step 1: Validate customer preferences
            await self._validate_customer_preferences(notification)
            
            # Step 2: Check rate limits
            await self._check_rate_limits(notification)
            
            # Step 3: Handle scheduled notifications
            if notification.scheduled_at:
                return await self._schedule_notification(notification)
            
            # Step 4: Process immediate delivery
            await self._process_immediate_delivery(notification)
            
            # Step 5: Store notification record
            await self._store_notification(notification)
            
            logger.info(f"Notification {notification.notification_id} processed successfully")
            return notification
            
        except Exception as e:
            # Handle errors and update notification status
            notification.status = NotificationStatus.FAILED
            notification.failure_reason = str(e)
            await self._store_notification(notification)
            
            logger.error(f"Failed to process notification {notification.notification_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_notification_status(self, notification_id: str) -> Notification:
        """
        Retrieve the current status and details of a notification.
        
        Args:
            notification_id: The unique identifier of the notification
            
        Returns:
            Notification: The notification with current status
            
        Raises:
            HTTPException: If notification is not found
        """
        notification_doc = await self.db.notifications.find_one(
            {"notification_id": notification_id}
        )
        
        if not notification_doc:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return Notification(**notification_doc)

    async def get_customer_preferences(self, customer_id: str) -> CustomerPreferences:
        """
        Retrieve notification preferences for a specific customer.
        
        Args:
            customer_id: The customer identifier
            
        Returns:
            CustomerPreferences: The customer's notification preferences
        """
        prefs_doc = await self.db.customer_preferences.find_one(
            {"customer_id": customer_id}
        )
        
        if not prefs_doc:
            # Return default preferences for new customers
            return CustomerPreferences(customer_id=customer_id)
        
        return CustomerPreferences(**prefs_doc)

    async def update_customer_preferences(self, preferences: CustomerPreferences) -> bool:
        """
        Update notification preferences for a customer.
        
        Args:
            preferences: The updated customer preferences
            
        Returns:
            bool: True if update was successful
        """
        result = await self.db.customer_preferences.update_one(
            {"customer_id": preferences.customer_id},
            {"$set": preferences.dict()},
            upsert=True
        )
        
        # Clear preferences cache
        await self.redis_client.delete(f"prefs:{preferences.customer_id}")
        
        return result.acknowledged

    async def send_transaction_alert(self, transaction_data: Dict[str, Any]) -> None:
        """
        Send transaction-related notifications with appropriate priority
        and channel selection based on transaction type and amount.
        
        Args:
            transaction_data: Dictionary containing transaction details
        """
        customer_id = transaction_data.get("customer_id")
        transaction_type = transaction_data.get("type")
        amount = float(transaction_data.get("amount", 0))
        
        # Determine notification priority based on transaction
        priority = NotificationPriority.NORMAL
        if amount >= 10000:  # High-value transactions
            priority = NotificationPriority.HIGH
        elif transaction_type in ["fraud_detected", "security_alert"]:
            priority = NotificationPriority.URGENT
        
        # Get customer preferences
        preferences = await self.get_customer_preferences(customer_id)
        
        # Select appropriate channel
        channel = self._select_optimal_channel(preferences, priority)
        
        # Create notification request
        request = NotificationRequest(
            customer_id=customer_id,
            channel=channel,
            template_id=f"transaction_{transaction_type}",
            priority=priority,
            recipient=await self._get_customer_contact(customer_id, channel),
            subject=f"Transaction {transaction_type.title()} - ${amount:,.2f}",
            content=await self._render_transaction_template(transaction_data),
            metadata={"transaction_id": transaction_data.get("transaction_id")}
        )
        
        # Send notification
        await self.send_notification(request)

    async def _validate_customer_preferences(self, notification: Notification) -> None:
        """
        Validate that the customer allows notifications for the specified channel
        and type, including quiet hours enforcement.
        """
        preferences = await self.get_customer_preferences(notification.customer_id)
        
        # Check if channel is enabled
        channel_enabled = getattr(preferences, f"{notification.channel.value}_enabled", True)
        if not channel_enabled:
            raise ValueError(f"Customer has disabled {notification.channel.value} notifications")
        
        # Check quiet hours for non-urgent notifications
        if (notification.priority != NotificationPriority.URGENT and 
            self._is_quiet_hours(preferences)):
            # Schedule for after quiet hours
            notification.scheduled_at = self._calculate_next_active_time(preferences)

    async def _check_rate_limits(self, notification: Notification) -> None:
        """
        Enforce rate limiting to prevent spam and comply with provider limits.
        Uses Redis for distributed rate limiting across service instances.
        """
        channel_limits = self.rate_limits.get(notification.channel, {})
        
        for period, limit in channel_limits.items():
            key = f"rate_limit:{notification.customer_id}:{notification.channel.value}:{period}"
            
            # Use Redis for atomic increment with expiry
            current = await self.redis_client.incr(key)
            if current == 1:
                # Set expiry based on period
                expiry = 3600 if period == "per_hour" else 60
                await self.redis_client.expire(key, expiry)
            
            if current > limit:
                raise ValueError(f"Rate limit exceeded for {notification.channel.value}: "
                               f"{current}/{limit} {period}")

    async def _process_immediate_delivery(self, notification: Notification) -> None:
        """
        Process immediate notification delivery through the appropriate channel
        with comprehensive error handling and retry logic.
        """
        try:
            if notification.channel == NotificationChannel.EMAIL:
                await self._send_email(notification)
            elif notification.channel == NotificationChannel.SMS:
                await self._send_sms(notification)
            elif notification.channel == NotificationChannel.PUSH:
                await self._send_push_notification(notification)
            else:
                raise ValueError(f"Unsupported notification channel: {notification.channel}")
            
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
            
        except Exception as e:
            # Implement retry logic for failed deliveries
            if notification.retry_count < 3:
                notification.retry_count += 1
                await self._schedule_retry(notification)
            else:
                notification.status = NotificationStatus.FAILED
                notification.failure_reason = str(e)
            raise

    async def _send_email(self, notification: Notification) -> None:
        """
        Send email notification using SendGrid with template rendering
        and delivery tracking.
        """
        message = Mail(
            from_email="noreply@bankingcorp.com",
            to_emails=notification.recipient,
            subject=notification.subject,
            html_content=notification.content
        )
        
        # Add tracking parameters
        message.tracking_settings = {
            "click_tracking": {"enable": True},
            "open_tracking": {"enable": True}
        }
        
        # Send email
        response = self.sendgrid_client.send(message)
        
        if response.status_code not in [200, 202]:
            raise Exception(f"SendGrid API error: {response.status_code}")
        
        logger.info(f"Email sent successfully to {notification.recipient}")

    async def _send_sms(self, notification: Notification) -> None:
        """
        Send SMS notification using Twilio with delivery confirmation
        and international support.
        """
        message = self.twilio_client.messages.create(
            body=notification.content,
            from_="+1234567890",  # Your Twilio phone number
            to=notification.recipient,
            status_callback="https://api.bankingcorp.com/webhooks/sms-status"
        )
        
        # Store message SID for delivery tracking
        notification.metadata["twilio_sid"] = message.sid
        
        logger.info(f"SMS sent successfully to {notification.recipient}")

    async def _send_push_notification(self, notification: Notification) -> None:
        """
        Send push notification using FCM/APNS with rich content support
        and device targeting.
        """
        # Implementation would use FCM for Android and APNS for iOS
        # This is a simplified example
        
        payload = {
            "notification": {
                "title": notification.subject,
                "body": notification.content,
                "icon": "banking_icon.png"
            },
            "data": notification.metadata
        }
        
        # Send to Firebase Cloud Messaging
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://fcm.googleapis.com/fcm/send",
                headers={
                    "Authorization": "key=your_fcm_server_key",
                    "Content-Type": "application/json"
                },
                json={"to": notification.recipient, **payload}
            ) as response:
                if response.status != 200:
                    raise Exception(f"FCM API error: {response.status}")
        
        logger.info(f"Push notification sent successfully to {notification.recipient}")

    async def _store_notification(self, notification: Notification) -> None:
        """
        Store notification record in MongoDB for audit trail and analytics.
        """
        await self.db.notifications.insert_one(notification.dict())

    async def _schedule_notification(self, notification: Notification) -> Notification:
        """
        Schedule notification for future delivery using background task processing.
        """
        # Store notification with scheduled status
        notification.status = NotificationStatus.PENDING
        await self._store_notification(notification)
        
        # Publish to Kafka for scheduled processing
        self.kafka_producer.send(
            "scheduled_notifications",
            value={
                "notification_id": notification.notification_id,
                "scheduled_at": notification.scheduled_at.isoformat()
            }
        )
        
        return notification

    def _is_quiet_hours(self, preferences: CustomerPreferences) -> bool:
        """
        Check if current time falls within customer's quiet hours.
        """
        current_time = datetime.now().time()
        
        if preferences.quiet_hours_start <= preferences.quiet_hours_end:
            # Same day quiet hours (e.g., 22:00 to 08:00 next day)
            return (current_time >= preferences.quiet_hours_start or 
                   current_time <= preferences.quiet_hours_end)
        else:
            # Overnight quiet hours (e.g., 22:00 to 08:00)
            return (preferences.quiet_hours_start <= current_time <= 
                   preferences.quiet_hours_end)

    def _select_optimal_channel(self, preferences: CustomerPreferences, 
                               priority: NotificationPriority) -> NotificationChannel:
        """
        Select the optimal notification channel based on customer preferences
        and notification priority.
        """
        if priority == NotificationPriority.URGENT:
            # For urgent notifications, prefer SMS if enabled
            if preferences.sms_enabled:
                return NotificationChannel.SMS
            elif preferences.push_enabled:
                return NotificationChannel.PUSH
        
        # Use customer's preferred channel if enabled
        preferred = preferences.preferred_channel
        if getattr(preferences, f"{preferred.value}_enabled", True):
            return preferred
        
        # Fallback to first available channel
        for channel in [NotificationChannel.EMAIL, NotificationChannel.SMS, 
                       NotificationChannel.PUSH]:
            if getattr(preferences, f"{channel.value}_enabled", True):
                return channel
        
        # Default to email if all else fails
        return NotificationChannel.EMAIL

# Global service instance
notification_service = NotificationService()

# FastAPI startup event
@app.on_event("startup")
async def startup_event():
    await notification_service.startup()

# API endpoints
@app.post("/api/v1/notifications/send", response_model=Notification)
async def send_notification_endpoint(request: NotificationRequest):
    """Send a notification through the specified channel"""
    return await notification_service.send_notification(request)

@app.get("/api/v1/notifications/{notification_id}", response_model=Notification)
async def get_notification_status_endpoint(notification_id: str):
    """Get the status of a specific notification"""
    return await notification_service.get_notification_status(notification_id)

@app.get("/api/v1/customers/{customer_id}/preferences", response_model=CustomerPreferences)
async def get_customer_preferences_endpoint(customer_id: str):
    """Get notification preferences for a customer"""
    return await notification_service.get_customer_preferences(customer_id)

@app.put("/api/v1/customers/{customer_id}/preferences")
async def update_customer_preferences_endpoint(
    customer_id: str, preferences: CustomerPreferences
):
    """Update notification preferences for a customer"""
    preferences.customer_id = customer_id
    success = await notification_service.update_customer_preferences(preferences)
    return {"success": success}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
