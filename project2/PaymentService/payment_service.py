from flask import Flask, request, jsonify
import json
import os
import pika

app = Flask(__name__)
DB_FILE = "payment_db.txt"

def read_db():
    if not os.path.exists(DB_FILE):
        return {"payments": {}}
    with open(DB_FILE, "r") as file:
        return json.load(file)

def write_db(data):
    with open(DB_FILE, "w") as file:
        json.dump(data, file, indent=4)

def is_valid_credit_card(number):
    # Luhn algorithm implementation
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d*2))
    return checksum % 10 == 0

def is_valid_expiration_date(month, year):
    # Simple expiration date check
    # Ensure month is between 1 and 12 and year is the current year or later
    from datetime import datetime
    current_year = datetime.now().year
    return 1 <= month <= 12 and year >= current_year

def is_valid_cvc(cvc):
    # CVC should be a three-digit number
    return isinstance(cvc, int) and 100 <= cvc <= 999

@app.route('/payment', methods=['POST'])
def process_payment():
    payment_data = request.json
    card_number = payment_data.get('creditCard', {}).get('cardNumber')
    expiration_month = payment_data.get('creditCard', {}).get('expirationMonth')
    expiration_year = payment_data.get('creditCard', {}).get('expirationYear')
    cvc = payment_data.get('creditCard', {}).get('cvc')
    db = read_db()

    # Perform validations
    if not is_valid_credit_card(card_number):
        return jsonify({"message": "Invalid credit card number"}), 400
    if not is_valid_expiration_date(expiration_month, expiration_year):
        return jsonify({"message": "Invalid expiration date"}), 400
    if not is_valid_cvc(cvc):
        return jsonify({"message": "Invalid CVC"}), 400

    payment_id = max(db['payments'].keys(), default=0, key=int) + 1
    db['payments'][payment_id] = payment_data
    write_db(db)

    # Send event to RabbitMQ (Payment-Successful or Payment-Failure)
    send_payment_event(payment_data, "Payment-Successful")

    return jsonify({"message": "Payment processed", "payment_id": payment_id}), 201

def send_payment_event(payment_data, event_type):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=event_type)

    channel.basic_publish(exchange='',
                          routing_key=event_type,
                          body=json.dumps(payment_data))
    connection.close()

if __name__ == '__main__':
    app.run(debug=True, port=8003)