from flask import Flask, request, jsonify
import json
import os
import pika

app = Flask(__name__)
DB_FILE = "db.txt"

def read_db():
    if not os.path.exists(DB_FILE):
        return {"merchants": {}, "buyers": {}, "products": {}, "orders": {}}
    with open(DB_FILE, "r") as file:
        return json.load(file)

def write_db(data):
    with open(DB_FILE, "w") as file:
        json.dump(data, file, indent=4)

def merchant_exists(merchant_id):
    db = read_db()
    return str(merchant_id) in db['merchants']

def buyer_exists(buyer_id):
    db = read_db()
    return str(buyer_id) in db['buyers']

def product_exists(product_id):
    db = read_db()
    return str(product_id) in db['products']

def product_sold_out(product_id):
    db = read_db()
    return db['products'][str(product_id)]['isSoldOut']

def product_belongs_to_merchant(product_id, merchant_id):
    db = read_db()
    return db['products'][str(product_id)]['merchantId'] == merchant_id

def merchant_allows_discount(merchant_id, discount):
    db = read_db()
    merchant = db['merchants'][str(merchant_id)]
    return discount == 0 or discount is None or merchant['allows_discount']

# Function to send a message to RabbitMQ
def send_order_created_event(order_data):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='order_created')

    channel.basic_publish(exchange='',
                          routing_key='order_created',
                          body=json.dumps(order_data))
    connection.close()

@app.route('/orders', methods=['POST'])
def create_order():
    order_data = request.json
    db = read_db()

    merchant_id = order_data.get('merchantId')
    buyer_id = order_data.get('buyerId')
    product_id = order_data.get('productId')
    discount = order_data.get('discount')

    # Validation checks
    if not merchant_exists(merchant_id):
        return jsonify({"message": "Merchant does not exist"}), 400

    if not buyer_exists(buyer_id):
        return jsonify({"message": "Buyer does not exist"}), 400

    if not product_exists(product_id):
        return jsonify({"message": "Product does not exist"}), 400

    if product_sold_out(product_id):
        return jsonify({"message": "Product is sold out"}), 400

    if not product_belongs_to_merchant(product_id, merchant_id):
        return jsonify({"message": "Product does not belong to merchant"}), 400

    if not merchant_allows_discount(merchant_id, discount):
        return jsonify({"message": "Merchant does not allow discount"}), 400

    # All validations passed, create the order
    order_id = max(db['orders'].keys(), default=0, key=int) + 1
    db['orders'][order_id] = order_data
    
    write_db(db)
    
    send_order_created_event(order_data)

    return jsonify({"message": "Order created", "order_id": order_id}), 201

@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    db = read_db()

    if str(order_id) in db['orders']:
        order = db['orders'][str(order_id)]
        return jsonify(order), 200

    return jsonify({"message": "Order does not exist"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=8000)