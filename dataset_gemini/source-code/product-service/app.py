import os
from flask import Flask, jsonify, request
import psycopg2 # This is imported but the comment below says MySQL

# --- DRIFT (Inline Comment) ---
# This inline comment is outdated. The code uses psycopg2 for PostgreSQL,
# but the comment explicitly states it connects to MySQL.
# This can mislead developers during maintenance.
# Connects to the MySQL database.
def get_db_connection():
    """Establishes a connection to the database."""
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        database=os.environ.get("DB_NAME", "products"),
        user=os.environ.get("DB_USER", "user"),
        password=os.environ.get("DB_PASSWORD", "password")
    )
    return conn

# --- DRIFT (Project-Level Documentation) ---
# The project's README.md and api_versioning_policy.md both state that all API
# endpoints MUST be prefixed with `/api/v1/`. This implementation omits that prefix,
# causing a drift from the project-wide standard.
app = Flask(__name__)

# Mock data for demonstration purposes if DB fails
mock_products = [
    {
        "productId": "prod-123", "name": "Wireless Mouse", "price": 25.99, "stock": 150,
        "description": "An ergonomic wireless mouse."
    },
    {
        "productId": "prod-456", "name": "Mechanical Keyboard", "price": 94.50, "stock": 75,
        "description": "A durable keyboard with RGB lighting."
    }
]

@app.route('/products', methods=['GET'])
def get_products():
    """
    Retrieves a list of all products from the database.
    Supports pagination via query parameters.

    Query Params:
        page (int): The page number to retrieve.
        limit (int): The number of items per page.

    Returns:
        A JSON response containing a list of products.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, name, price, stock, description FROM products;')
        products = cur.fetchall()
        cur.close()
        conn.close()

        # Format the result into a list of dictionaries
        product_list = []
        for p in products:
            product_list.append({
                "productId": p[0], "name": p[1], "price": float(p[2]), "stock": p[3], "description": p[4]
            })
        return jsonify(product_list)
    except Exception as e:
        print(f"Database connection failed: {e}")
        # Fallback to mock data if the database is unavailable
        return jsonify(mock_products)

@app.route('/products/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    """
    Retrieves details for a specific product by its ID.

    Args:
        product_id (str): The unique identifier for the product.

    Returns:
        A JSON response with the product's details or a 404 error.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, name, price, stock, description FROM products WHERE id = %s;', (product_id,))
        product = cur.fetchone()
        cur.close()
        conn.close()

        if product is None:
            return jsonify({"error": "Product not found"}), 404
        else:
            return jsonify({
                "productId": product[0], "name": product[1], "price": float(product[2]),
                "stock": product[3], "description": product[4]
            })
    except Exception as e:
        print(f"Database connection failed: {e}")
        # Fallback to mock data
        found_product = next((p for p in mock_products if p["productId"] == product_id), None)
        if found_product:
            return jsonify(found_product)
        return jsonify({"error": "Product not found"}), 404

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for the service.
    This is compliant with the architectural guidelines.
    """
    # Simple health check, can be expanded to check DB connection
    return jsonify({"status": "UP"}), 200

def some_internal_logic():
    """Placeholder for more complex business logic."""
    print("Executing some internal helper function.")
    return True

def validate_product_data(data):
    """Validates incoming product data."""
    if not data or 'name' not in data or 'price' not in data:
        return False
    return True

if __name__ == '__main__':
    # --- DRIFT (Organization-Level Documentation) ---
    # The coding_standards.md states that variables should be camelCase.
    # The variable `debug_mode` uses snake_case, which is common in Python
    # but violates the organization's cross-language standard.
    debug_mode = os.environ.get("DEBUG_MODE", "True").lower() == "true"
    app.run(host='0.0.0.0', port=5001, debug=debug_mode)
