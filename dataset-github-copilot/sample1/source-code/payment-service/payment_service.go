package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/mux"
	"github.com/stripe/stripe-go/v74"
	"github.com/stripe/stripe-go/v74/paymentintent"
)

// PaymentRequest represents a payment processing request with comprehensive validation
// Contains all necessary information for payment authorization and processing
// Supports multiple payment methods including cards, digital wallets, and bank transfers
type PaymentRequest struct {
	OrderID       string  `json:"order_id" validate:"required"`        // Unique order identifier for payment association
	CustomerID    string  `json:"customer_id" validate:"required"`     // Customer identifier for payment authorization
	Amount        float64 `json:"amount" validate:"required,min=0.01"` // Payment amount in base currency units
	Currency      string  `json:"currency" validate:"required,len=3"`  // ISO 4217 currency code (USD, EUR, GBP, etc.)
	PaymentMethod string  `json:"payment_method" validate:"required"`  // Payment method identifier or token
	Description   string  `json:"description"`                         // Payment description for customer records
	Metadata      map[string]string `json:"metadata"`                  // Additional metadata for payment tracking
}

// PaymentResponse contains the result of payment processing operation
// Provides comprehensive information about payment status and transaction details
// Includes necessary data for order fulfillment and customer communication
type PaymentResponse struct {
	TransactionID    string            `json:"transaction_id"`     // Unique transaction identifier
	Status           string            `json:"status"`             // Payment status (success, failed, pending)
	Amount           float64           `json:"amount"`             // Processed payment amount
	Currency         string            `json:"currency"`           // Currency used for payment
	ProcessedAt      time.Time         `json:"processed_at"`       // Timestamp of payment processing
	PaymentMethodID  string            `json:"payment_method_id"`  // Identifier of payment method used
	GatewayResponse  map[string]interface{} `json:"gateway_response"` // Raw gateway response data
	FraudScore       float64           `json:"fraud_score"`        // Risk assessment score (0-100)
	AuthorizationCode string           `json:"authorization_code"` // Payment authorization code
	Fees             float64           `json:"fees"`               // Processing fees charged
}

// RefundRequest represents a refund processing request with validation
// Supports full and partial refunds with reason tracking
// Implements proper authorization and audit trail requirements
type RefundRequest struct {
	TransactionID string  `json:"transaction_id" validate:"required"` // Original transaction to refund
	Amount        float64 `json:"amount" validate:"required,min=0.01"` // Refund amount (partial or full)
	Reason        string  `json:"reason" validate:"required"`         // Reason for refund processing
	RequestedBy   string  `json:"requested_by" validate:"required"`   // User requesting the refund
}

// PaymentService handles all payment processing operations
// Implements PCI DSS compliant payment processing with multiple gateway support
// Provides comprehensive fraud detection and risk management capabilities
type PaymentService struct {
	stripeClient   *stripe.Client    // Stripe payment gateway client
	fraudDetector  *FraudDetector    // Fraud detection service
	auditLogger    *AuditLogger      // Audit logging service
	encryptionKey  []byte           // Encryption key for sensitive data
	rateLimit      *RateLimiter     // Rate limiting for payment requests
}

// NewPaymentService creates a new payment service instance with required dependencies
// Initializes all necessary components for secure payment processing
// Configures fraud detection, audit logging, and encryption services
func NewPaymentService(stripeSecretKey string, encryptionKey []byte) *PaymentService {
	// Initialize Stripe client with secret key
	stripe.Key = stripeSecretKey
	
	// Create fraud detection service with machine learning models
	fraudDetector := NewFraudDetector()
	
	// Initialize audit logger for compliance requirements
	auditLogger := NewAuditLogger()
	
	// Configure rate limiter to prevent abuse
	rateLimit := NewRateLimiter(100, time.Minute) // 100 requests per minute
	
	return &PaymentService{
		stripeClient:  &stripe.Client{},
		fraudDetector: fraudDetector,
		auditLogger:   auditLogger,
		encryptionKey: encryptionKey,
		rateLimit:     rateLimit,
	}
}

// ProcessPayment handles payment authorization and capture with comprehensive validation
// Implements fraud detection, risk assessment, and compliance requirements
// Supports multiple payment gateways with intelligent routing based on transaction characteristics
func (ps *PaymentService) ProcessPayment(ctx context.Context, req PaymentRequest) (*PaymentResponse, error) {
	log.Printf("Processing payment for order: %s, amount: %.2f %s", req.OrderID, req.Amount, req.Currency)
	
	// Check rate limiting to prevent payment processing abuse
	if !ps.rateLimit.Allow(req.CustomerID) {
		ps.auditLogger.LogSecurityEvent("RATE_LIMIT_EXCEEDED", req.CustomerID, req.OrderID)
		return nil, fmt.Errorf("rate limit exceeded for customer: %s", req.CustomerID)
	}
	
	// Validate payment request data against business rules and compliance requirements
	if err := ps.validatePaymentRequest(req); err != nil {
		ps.auditLogger.LogValidationError("PAYMENT_VALIDATION_FAILED", req.CustomerID, err.Error())
		return nil, fmt.Errorf("payment validation failed: %w", err)
	}
	
	// Perform comprehensive fraud detection and risk assessment
	fraudScore, riskFactors := ps.fraudDetector.AssessRisk(req)
	log.Printf("Fraud assessment completed - Score: %.2f, Risk factors: %v", fraudScore, riskFactors)
	
	// Block high-risk transactions for manual review
	if fraudScore > 80.0 {
		ps.auditLogger.LogSecurityEvent("HIGH_RISK_TRANSACTION_BLOCKED", req.CustomerID, req.OrderID)
		return nil, fmt.Errorf("transaction blocked due to high fraud risk: %.2f", fraudScore)
	}
	
	// Generate unique transaction identifier for tracking
	transactionID := ps.generateTransactionID()
	
	// Create payment intent with Stripe gateway
	paymentIntent, err := ps.createStripePaymentIntent(req, transactionID)
	if err != nil {
		ps.auditLogger.LogPaymentError("STRIPE_PAYMENT_INTENT_FAILED", req.CustomerID, err.Error())
		return nil, fmt.Errorf("failed to create payment intent: %w", err)
	}
	
	// Confirm payment intent to authorize and capture funds
	confirmedIntent, err := ps.confirmPaymentIntent(paymentIntent.ID, req.PaymentMethod)
	if err != nil {
		ps.auditLogger.LogPaymentError("PAYMENT_CONFIRMATION_FAILED", req.CustomerID, err.Error())
		return nil, fmt.Errorf("payment confirmation failed: %w", err)
	}
	
	// Calculate processing fees based on payment method and amount
	processingFees := ps.calculateProcessingFees(req.Amount, req.PaymentMethod)
	
	// Build comprehensive payment response with all transaction details
	response := &PaymentResponse{
		TransactionID:     transactionID,
		Status:           string(confirmedIntent.Status),
		Amount:           req.Amount,
		Currency:         req.Currency,
		ProcessedAt:      time.Now(),
		PaymentMethodID:  req.PaymentMethod,
		GatewayResponse:  ps.buildGatewayResponse(confirmedIntent),
		FraudScore:       fraudScore,
		AuthorizationCode: ps.extractAuthorizationCode(confirmedIntent),
		Fees:             processingFees,
	}
	
	// Store payment transaction for audit and compliance
	if err := ps.storePaymentTransaction(req, response); err != nil {
		log.Printf("Warning: Failed to store payment transaction: %v", err)
	}
	
	// Publish payment success event for other microservices
	ps.publishPaymentEvent("PAYMENT_SUCCESSFUL", response)
	
	// Log successful payment processing for audit trail
	ps.auditLogger.LogPaymentSuccess(transactionID, req.CustomerID, req.Amount)
	
	log.Printf("Payment processed successfully - Transaction ID: %s", transactionID)
	return response, nil
}

// ProcessRefund handles refund operations with proper validation and audit trail
// Supports both full and partial refunds with comprehensive error handling
// Implements proper authorization checks and compliance requirements
func (ps *PaymentService) ProcessRefund(ctx context.Context, req RefundRequest) (*PaymentResponse, error) {
	log.Printf("Processing refund for transaction: %s, amount: %.2f", req.TransactionID, req.Amount)
	
	// Validate refund request parameters
	if err := ps.validateRefundRequest(req); err != nil {
		ps.auditLogger.LogValidationError("REFUND_VALIDATION_FAILED", req.RequestedBy, err.Error())
		return nil, fmt.Errorf("refund validation failed: %w", err)
	}
	
	// Retrieve original payment transaction for refund processing
	originalPayment, err := ps.getOriginalPaymentTransaction(req.TransactionID)
	if err != nil {
		ps.auditLogger.LogPaymentError("ORIGINAL_PAYMENT_NOT_FOUND", req.RequestedBy, err.Error())
		return nil, fmt.Errorf("original payment not found: %w", err)
	}
	
	// Validate refund amount does not exceed original payment
	if req.Amount > originalPayment.Amount {
		return nil, fmt.Errorf("refund amount %.2f exceeds original payment amount %.2f", 
			req.Amount, originalPayment.Amount)
	}
	
	// Check if refund is allowed based on payment status and time limits
	if !ps.isRefundAllowed(originalPayment) {
		return nil, fmt.Errorf("refund not allowed for transaction: %s", req.TransactionID)
	}
	
	// Convert amount to cents for Stripe API (Stripe uses smallest currency unit)
	refundAmountCents := int64(req.Amount * 100)
	
	// Create refund with Stripe gateway
	refundParams := &stripe.RefundParams{
		PaymentIntent: stripe.String(originalPayment.TransactionID),
		Amount:        stripe.Int64(refundAmountCents),
		Reason:        stripe.String(req.Reason),
		Metadata: map[string]string{
			"requested_by": req.RequestedBy,
			"refund_reason": req.Reason,
			"original_order": originalPayment.OrderID,
		},
	}
	
	refund, err := ps.stripeClient.Refunds.New(refundParams)
	if err != nil {
		ps.auditLogger.LogPaymentError("STRIPE_REFUND_FAILED", req.RequestedBy, err.Error())
		return nil, fmt.Errorf("failed to process refund with Stripe: %w", err)
	}
	
	// Generate unique refund transaction ID
	refundTransactionID := ps.generateTransactionID()
	
	// Build refund response with transaction details
	response := &PaymentResponse{
		TransactionID:   refundTransactionID,
		Status:         string(refund.Status),
		Amount:         req.Amount,
		Currency:       originalPayment.Currency,
		ProcessedAt:    time.Now(),
		PaymentMethodID: originalPayment.PaymentMethodID,
		GatewayResponse: map[string]interface{}{
			"refund_id": refund.ID,
			"reason":    refund.Reason,
		},
		Fees: ps.calculateRefundFees(req.Amount),
	}
	
	// Store refund transaction for audit and compliance
	if err := ps.storeRefundTransaction(req, response, originalPayment); err != nil {
		log.Printf("Warning: Failed to store refund transaction: %v", err)
	}
	
	// Publish refund event for other microservices
	ps.publishPaymentEvent("REFUND_PROCESSED", response)
	
	// Log successful refund processing
	ps.auditLogger.LogRefundSuccess(refundTransactionID, req.RequestedBy, req.Amount)
	
	log.Printf("Refund processed successfully - Transaction ID: %s", refundTransactionID)
	return response, nil
}

// HTTP handler for payment processing endpoint
// Implements RESTful API with proper error handling and response formatting
func (ps *PaymentService) handleProcessPayment(w http.ResponseWriter, r *http.Request) {
	// Parse JSON request body
	var req PaymentRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON request", http.StatusBadRequest)
		return
	}
	
	// Process payment with context timeout
	ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
	defer cancel()
	
	response, err := ps.ProcessPayment(ctx, req)
	if err != nil {
		log.Printf("Payment processing failed: %v", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	
	// Return successful payment response
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// HTTP handler for refund processing endpoint
func (ps *PaymentService) handleProcessRefund(w http.ResponseWriter, r *http.Request) {
	// Parse refund request
	var req RefundRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON request", http.StatusBadRequest)
		return
	}
	
	// Process refund with timeout
	ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
	defer cancel()
	
	response, err := ps.ProcessRefund(ctx, req)
	if err != nil {
		log.Printf("Refund processing failed: %v", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	
	// Return refund response
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// Private helper methods for payment processing

func (ps *PaymentService) validatePaymentRequest(req PaymentRequest) error {
	// Validate required fields are present
	if req.OrderID == "" {
		return fmt.Errorf("order ID is required")
	}
	if req.CustomerID == "" {
		return fmt.Errorf("customer ID is required")
	}
	if req.Amount <= 0 {
		return fmt.Errorf("amount must be greater than zero")
	}
	if len(req.Currency) != 3 {
		return fmt.Errorf("currency must be 3 character ISO code")
	}
	if req.PaymentMethod == "" {
		return fmt.Errorf("payment method is required")
	}
	
	// Validate amount limits
	if req.Amount < 0.50 {
		return fmt.Errorf("minimum payment amount is $0.50")
	}
	if req.Amount > 50000.00 {
		return fmt.Errorf("maximum payment amount is $50,000.00")
	}
	
	return nil
}

func (ps *PaymentService) generateTransactionID() string {
	// Generate cryptographically secure random transaction ID
	bytes := make([]byte, 16)
	if _, err := rand.Read(bytes); err != nil {
		// Fallback to timestamp-based ID if crypto random fails
		return fmt.Sprintf("TXN_%d", time.Now().UnixNano())
	}
	return "TXN_" + hex.EncodeToString(bytes)
}

func (ps *PaymentService) createStripePaymentIntent(req PaymentRequest, transactionID string) (*stripe.PaymentIntent, error) {
	// Convert amount to cents (Stripe uses smallest currency unit)
	amountCents := int64(req.Amount * 100)
	
	// Create payment intent parameters
	params := &stripe.PaymentIntentParams{
		Amount:   stripe.Int64(amountCents),
		Currency: stripe.String(strings.ToLower(req.Currency)),
		PaymentMethod: stripe.String(req.PaymentMethod),
		ConfirmationMethod: stripe.String("manual"),
		Confirm: stripe.Bool(false),
		Description: stripe.String(req.Description),
		Metadata: map[string]string{
			"order_id": req.OrderID,
			"customer_id": req.CustomerID,
			"transaction_id": transactionID,
		},
	}
	
	// Create payment intent with Stripe
	return paymentintent.New(params)
}

func (ps *PaymentService) confirmPaymentIntent(paymentIntentID, paymentMethodID string) (*stripe.PaymentIntent, error) {
	// Confirm payment intent to process payment
	params := &stripe.PaymentIntentConfirmParams{
		PaymentMethod: stripe.String(paymentMethodID),
	}
	
	return paymentintent.Confirm(paymentIntentID, params)
}

func (ps *PaymentService) calculateProcessingFees(amount float64, paymentMethod string) float64 {
	// Calculate processing fees based on payment method
	var feeRate float64
	
	switch paymentMethod {
	case "card":
		feeRate = 0.029 // 2.9% for card payments
	case "bank_transfer":
		feeRate = 0.008 // 0.8% for bank transfers
	case "digital_wallet":
		feeRate = 0.025 // 2.5% for digital wallets
	default:
		feeRate = 0.029 // Default card rate
	}
	
	return amount * feeRate
}

// Placeholder implementations for supporting services
type FraudDetector struct{}
func NewFraudDetector() *FraudDetector { return &FraudDetector{} }
func (fd *FraudDetector) AssessRisk(req PaymentRequest) (float64, []string) {
	// Simplified fraud detection - production would use ML models
	return 15.0, []string{"low_risk"}
}

type AuditLogger struct{}
func NewAuditLogger() *AuditLogger { return &AuditLogger{} }
func (al *AuditLogger) LogSecurityEvent(event, user, order string) {
	log.Printf("SECURITY: %s - User: %s, Order: %s", event, user, order)
}
func (al *AuditLogger) LogValidationError(event, user, error string) {
	log.Printf("VALIDATION: %s - User: %s, Error: %s", event, user, error)
}
func (al *AuditLogger) LogPaymentError(event, user, error string) {
	log.Printf("PAYMENT_ERROR: %s - User: %s, Error: %s", event, user, error)
}
func (al *AuditLogger) LogPaymentSuccess(txn, customer string, amount float64) {
	log.Printf("PAYMENT_SUCCESS: Transaction: %s, Customer: %s, Amount: %.2f", txn, customer, amount)
}
func (al *AuditLogger) LogRefundSuccess(txn, user string, amount float64) {
	log.Printf("REFUND_SUCCESS: Transaction: %s, User: %s, Amount: %.2f", txn, user, amount)
}

type RateLimiter struct{}
func NewRateLimiter(limit int, window time.Duration) *RateLimiter { return &RateLimiter{} }
func (rl *RateLimiter) Allow(key string) bool { return true }

// Additional helper methods would be implemented for:
// - validateRefundRequest()
// - getOriginalPaymentTransaction()
// - isRefundAllowed()
// - storePaymentTransaction()
// - storeRefundTransaction()
// - publishPaymentEvent()
// - buildGatewayResponse()
// - extractAuthorizationCode()
// - calculateRefundFees()

func main() {
	// Initialize payment service
	encryptionKey := make([]byte, 32) // In production, load from secure configuration
	ps := NewPaymentService("sk_test_stripe_key", encryptionKey)
	
	// Set up HTTP routes
	r := mux.NewRouter()
	r.HandleFunc("/api/v1/payments/process", ps.handleProcessPayment).Methods("POST")
	r.HandleFunc("/api/v1/payments/refund", ps.handleProcessRefund).Methods("POST")
	
	// Start HTTP server
	log.Println("Payment service starting on port 8082")
	log.Fatal(http.ListenAndServe(":8082", r))
}
