from flask import Flask, render_template, request, jsonify
from database import get_connection

app = Flask(__name__)

# -------------------- Web Page Routes --------------------

@app.route('/')
def home():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total_products FROM products")
    total_products = cur.fetchone()['total_products']

    cur.execute("SELECT COUNT(*) AS total_customers FROM customers")
    total_customers = cur.fetchone()['total_customers']

    cur.execute("SELECT SUM(total_price) AS stock_in_total FROM stock_transactions WHERE transaction_type = 'Stock In'")
    stock_in_result = cur.fetchone()['stock_in_total'] or 0
    stock_in = round(stock_in_result, 2)

    cur.execute("SELECT SUM(total_price) AS stock_out_total FROM stock_transactions WHERE transaction_type = 'Stock Out'")
    stock_out_result = cur.fetchone()['stock_out_total'] or 0
    stock_out = round(stock_out_result, 2)

    cur.execute(""" 
        SELECT p.product_name, SUM(st.quantity) AS total_quantity
        FROM stock_transactions st
        JOIN products p ON st.product_id = p.id
        WHERE st.transaction_type = 'Stock Out'
        GROUP BY st.product_id
        ORDER BY total_quantity DESC
        LIMIT 1
    """)
    top_product_row = cur.fetchone()
    top_product = top_product_row['product_name'] if top_product_row else "N/A"

    cur.execute("SELECT category, COUNT(*) AS count FROM products GROUP BY category")
    category_data = cur.fetchall()
    categories = [row['category'] for row in category_data]
    category_counts = [row['count'] for row in category_data]

    cur.execute("SELECT SUM(stock_value) AS total_stock_value FROM products")
    total_stock_value = cur.fetchone()['total_stock_value'] or 0

    cur.close()
    conn.close()

    return render_template('index.html',
                           total_products=total_products,
                           total_customers=total_customers,
                           stock_in=stock_in,
                           stock_out=stock_out,
                           top_product=top_product,
                           categories=categories,
                           category_counts=category_counts,
                           total_stock_value=round(total_stock_value, 2))

@app.route('/product')
def product():
    return render_template('product.html')

@app.route('/customer')
def customer():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM customers")
    customers = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('customer.html', customers=customers)

@app.route('/report')
def report():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute(""" 
        SELECT st.customer_name, p.product_name, st.quantity, st.transaction_date, 
               st.total_price AS total
        FROM stock_transactions st
        JOIN products p ON st.product_id = p.id
        WHERE st.transaction_type = 'Stock Out'
        ORDER BY st.transaction_date DESC
    """)
    sales_data = cur.fetchall()

    cur.execute("SELECT * FROM products")
    stock_data = cur.fetchall()

    cur.execute("SELECT * FROM products WHERE stock_level < 5")
    low_stock_data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('report.html', sales=sales_data, stock=stock_data, lowstock=low_stock_data)

@app.route('/stockinout')
def stockinout():
    return render_template('stockinout.html')

@app.route('/transactions')
def transactions():
    return render_template('transactions.html')

# -------------------- Product APIs --------------------

@app.route('/add_product', methods=['POST'])
def add_product():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO products (product_name, SKU, category, stock_level, stock_value)
        VALUES (%s, %s, %s, %s, %s)
    """, (data['product_name'], data['SKU'], data['category'],
          int(data['stock_level']), float(data['stock_value'])))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Product added successfully"}), 200

@app.route('/update_product/<int:id>', methods=['POST'])
def update_product(id):
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE products
        SET product_name = %s, SKU = %s, category = %s, stock_level = %s, stock_value = %s
        WHERE id = %s
    """, (data['product_name'], data['SKU'], data['category'],
          int(data['stock_level']), float(data['stock_value']), id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Product updated successfully"}), 200

@app.route('/delete_product/<int:id>', methods=['POST'])
def delete_product(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Product deleted successfully"}), 200

@app.route('/get_products')
def get_products():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"products": products})

# -------------------- Customer APIs --------------------

@app.route('/add_customer', methods=['POST'])
def add_customer():
    data = request.json
    customer_id = data['customer_id']

    if len(customer_id) != 5:
        return jsonify({"error": "Customer ID must be 5 characters long"}), 400

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM customers WHERE customer_id = %s", (customer_id,))
    if cur.fetchone()[0] > 0:
        return jsonify({"error": "Customer ID already exists, please choose a unique ID"}), 400

    cur.execute("""
        INSERT INTO customers (customer_id, customer_name, phone, address)
        VALUES (%s, %s, %s, %s)
    """, (customer_id, data['customer_name'], data['phone'], data['address']))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": f"Customer added successfully! Customer ID: {customer_id}"}), 200

@app.route('/get_customers')
def get_customers():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT customer_id, customer_name, phone, address FROM customers")
    customers = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"customers": customers})

@app.route('/update_customer/<int:id>', methods=['POST'])
def update_customer(id):
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE customers
        SET customer_name = %s, phone = %s, address = %s
        WHERE id = %s
    """, (data['customer_name'], data['phone'], data['address'], id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Customer updated successfully"}), 200

@app.route('/delete_customer/<int:id>', methods=['POST'])
def delete_customer(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM customers WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Customer deleted successfully"}), 200

# -------------------- Stock Transactions --------------------

@app.route('/stock_in_bulk', methods=['POST'])
def stock_in_bulk():
    data = request.json
    items = data.get('items', [])
    if not items:
        return jsonify({"error": "No items provided for stock in"}), 400

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity')
            price = item.get('price')
            customer_name = item.get('customer_name')

            if not all([product_id, quantity, price, customer_name]):
                return jsonify({"error": "Missing required fields"}), 400

            total_price = quantity * price

            cur.execute("SELECT stock_level, stock_value FROM products WHERE id = %s", (product_id,))
            product = cur.fetchone()
            if not product:
                return jsonify({"error": f"Product with ID {product_id} not found"}), 404

            cur.execute(""" 
                INSERT INTO stock_transactions (transaction_type, product_id, quantity, customer_name, total_price)
                VALUES ('Stock In', %s, %s, %s, %s)
            """, (product_id, quantity, customer_name, total_price))

            cur.execute("""
                UPDATE products
                SET stock_level = stock_level + %s, stock_value = stock_value + %s
                WHERE id = %s
            """, (quantity, total_price, product_id))

        conn.commit()
        return jsonify({"message": "Stock In transactions successful"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/stock_out_bulk', methods=['POST'])
def stock_out_bulk():
    data = request.json
    items = data.get('items', [])

    if not items:
        return jsonify({"error": "No items provided for stock out"}), 400

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity')
            price = item.get('price')
            customer_name = item.get('customer_name')

            if not all([product_id, quantity, price, customer_name]):
                return jsonify({"error": "Missing required fields"}), 400

            cur.execute("SELECT stock_level, stock_value FROM products WHERE id = %s", (product_id,))
            product = cur.fetchone()

            if not product:
                return jsonify({"error": f"Product with ID {product_id} not found"}), 404

            current_stock = product['stock_level']
            if quantity > current_stock:
                return jsonify({"error": f"Not enough stock for product {product_id}"}), 400

            unit_cost_price = product['stock_value'] / current_stock if current_stock else 0
            stock_out_cost = quantity * unit_cost_price
            stock_out_price = quantity * price

            cur.execute(""" 
                INSERT INTO stock_transactions (transaction_type, product_id, quantity, customer_name, total_price)
                VALUES ('Stock Out', %s, %s, %s, %s)
            """, (product_id, quantity, customer_name, stock_out_price))

            cur.execute(""" 
                UPDATE products
                SET stock_level = stock_level - %s, stock_value = GREATEST(stock_value - %s, 0)
                WHERE id = %s
            """, (quantity, stock_out_cost, product_id))

        conn.commit()
        return jsonify({"message": "Stock Out transactions successful"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/get_transactions')
def get_transactions():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT st.transaction_date, p.product_name, st.quantity, st.transaction_type, 
               st.customer_name, st.total_price
        FROM stock_transactions st
        JOIN products p ON st.product_id = p.id
        ORDER BY st.transaction_date DESC
    """)
    transactions = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"transactions": transactions})



# -------------------- Run Flask App --------------------

if __name__ == '__main__':
    app.run(debug=True)
