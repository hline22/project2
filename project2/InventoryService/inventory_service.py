from flask import Flask, request, jsonify
import json
import os
import pika
import threading

app = Flask(__name__)
DB_FILE = "inventory_db.txt"

def read_db():
    if not os.path.exists(DB_FILE):
        return {"products": {}}
    with open(DB_FILE, "r") as file:
        return json.load(file)

def write_db(data):
    with open(DB_FILE, "w") as file:
        json.dump(data, file, indent=4)

@app.route('/products', methods=['POST'])
def create_product():
    product_data = request.json
    db = read_db()
    product_id = max(db['products'].keys(), default=0, key=int) + 1
    product_data["reserved"] = 0  # Initialize reserved quantity
    db['products'][product_id] = product_data
    write_db(db)
    return jsonify({"message": "Product created", "product_id": product_id}), 201

@app.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    db = read_db()
    if str(product_id) in db['products']:
        return jsonify(db['products'][str(product_id)]), 200
    return jsonify({"message": "Product does not exist"}), 404


def update_product_stock(order_id, success):
    db = read_db()
    order_data = db.get('orders', {}).get(order_id, {})
    product_id = order_data.get('product_id')
    reserved_quantity = order_data.get('quantity', 0)

    if product_id in db['products']:
        product = db['products'][product_id]
        if success:
            # On payment success, decrease stock and reset reservation
            product['quantity'] = max(0, product['quantity'] - reserved_quantity)
        # On both success and failure, reset the reserved quantity
        product['reserved'] = max(0, product['reserved'] - reserved_quantity)
        db['products'][product_id] = product
        write_db(db)

def process_payment_success(body):
    data = json.loads(body)
    order_id = data['order_id']
    update_product_stock(order_id, success=True)

def process_payment_failure(body):
    data = json.loads(body)
    order_id = data['order_id']
    update_product_stock(order_id, success=False)

def start_rabbitmq_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='payment_success')
    channel.queue_declare(queue='payment_failure')

    def callback(ch, method, properties, body):
        if method.routing_key == 'payment_success':
            process_payment_success(body)
        elif method.routing_key == 'payment_failure':
            process_payment_failure(body)

    channel.basic_consume(queue='payment_success', on_message_callback=callback, auto_ack=True)
    channel.basic_consume(queue='payment_failure', on_message_callback=callback, auto_ack=True)

    channel.start_consuming()

if __name__ == '__main__':
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
    app.run(debug=True, port=8003)
