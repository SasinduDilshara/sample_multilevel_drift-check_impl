package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"time"
)

// PaymentRequest defines the structure for an incoming payment request.
// All fields use camelCase as per the organization's coding standards.
type PaymentRequest struct {
	OrderID     string  `json:"orderId"`
	Amount      float64 `json:"amount"`
	CreditCard  string  `json:"creditCard"`
	ExpiryMonth int     `json:"expiryMonth"`
	ExpiryYear  int     `json:"expiryYear"`
	CVV         string  `json:"cvv"`
}

// PaymentResponse defines the structure for a payment response.
type PaymentResponse struct {
	TransactionID string `json:"transactionId"`
	Status        string `json:"status"`
	Message       string `json:"message"`
}

// A simple logging function that adheres to the org-wide format.
func logRequest(level, message string) {
	// Compliant with [LEVEL] - {YYYY-MM-DD HH:mm:ss} - Message
	timestamp := time.Now().UTC().Format("2006-01-02 15:04:05")
	log.Printf("[%s] - %s - %s", level, timestamp, message)
}

// processPaymentHandler handles the /api/v1/process-payment endpoint.
// It validates the request and simulates a payment transaction.
func processPaymentHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req PaymentRequest
	decoder := json.NewDecoder(r.Body)
	err := decoder.Decode(&req)
	if err != nil {
		logRequest("ERROR", "Failed to decode payment request body")
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	logRequest("INFO", "Processing payment for OrderID: "+req.OrderID)

	// Basic validation, as per security policies.
	if !validatePaymentRequest(req) {
		logRequest("WARN", "Invalid payment data for OrderID: "+req.OrderID)
		http.Error(w, "Invalid payment data", http.StatusBadRequest)
		return
	}

	// Simulate payment processing with an external gateway.
	// This would involve a call to Stripe, Braintree, etc.
	time.Sleep(1 * time.Second) // Simulate network latency.

	// In a real app, the transaction ID would come from the payment gateway.
	transactionID := "txn_" + req.OrderID
	status := "SUCCESS"
	message := "Payment processed successfully."

	response := PaymentResponse{
		TransactionID: transactionID,
		Status:        status,
		Message:       message,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}

// validatePaymentRequest performs basic checks on the incoming payment data.
func validatePaymentRequest(req PaymentRequest) bool {
	if req.OrderID == "" || req.Amount <= 0 || len(req.CreditCard) != 16 || len(req.CVV) != 3 {
		return false
	}
	// Add more validation for expiry date, card number format (Luhn algorithm), etc.
	return true
}

// healthCheckHandler provides a health check endpoint for the service.
func healthCheckHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("Payment service is UP"))
}

// refundPaymentHandler is a placeholder for a refund endpoint.
func refundPaymentHandler(w http.ResponseWriter, r *http.Request) {
	logRequest("INFO", "Refund requested")
	w.WriteHeader(http.StatusNotImplemented)
	w.Write([]byte("Refund functionality not implemented yet."))
}

// getTransactionStatusHandler is another placeholder for a status check endpoint.
func getTransactionStatusHandler(w http.ResponseWriter, r *http.Request) {
	logRequest("INFO", "Transaction status requested")
	w.WriteHeader(http.StatusNotImplemented)
	w.Write([]byte("Transaction status functionality not implemented yet."))
}

func main() {
	// This setup is fully compliant with all known documentation.
	// It uses the /api/v1/ prefix and exposes a /health endpoint.
	mux := http.NewServeMux()
	mux.HandleFunc("/api/v1/process-payment", processPaymentHandler)
	mux.HandleFunc("/api/v1/refund", refundPaymentHandler)
	mux.HandleFunc("/api/v1/transaction/status", getTransactionStatusHandler)
	mux.HandleFunc("/health", healthCheckHandler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8083" // Default port if not specified
	}

	logRequest("INFO", "Payment Service starting on port "+port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("Could not start server: %s\n", err)
	}
}
