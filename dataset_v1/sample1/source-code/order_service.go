// Order Service
// Project-level docs require refund support (missing here)
package main

import "fmt"

// PlaceOrder handles order placement
func PlaceOrder(orderId string) string {
    return fmt.Sprintf("Order %s placed", orderId)
}
