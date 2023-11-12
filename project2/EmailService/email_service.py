from flask import Flask
import os
import json
import pika
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_SENDER_EMAIL = os.getenv("SENDGRID_SENDER_EMAIL")
sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

def read_db():
    if not os.path.exists("email_db.txt"):
        return {}
    with open("email_db.txt", "r") as file:
        return json.load(file)

def get_email_addresses(order_id):
    db = read_db()
    order = db.get('orders', {}).get(str(order_id), {})
    buyer_id = order.get('buyerId')
    merchant_id = order.get('merchantId')

    buyer_email = db.get('buyers', {}).get(str(buyer_id), {}).get('email')
    merchant_email = db.get('merchants', {}).get(str(merchant_id), {}).get('email')

    return buyer_email, merchant_email

def send_email(subject, body, to_emails):
    from_email = Email(SENDGRID_SENDER_EMAIL)
    to_email = To(to_emails)
    content = Content("text/plain", body)
    mail = Mail(from_email, to_email, subject, content)
    response = sg.client.mail.send.post(request_body=mail.get())
    return response

def start_rabbitmq_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='order_created')
    channel.queue_declare(queue='payment_success')
    channel.queue_declare(queue='payment_failure')

    def callback(ch, method, properties, body):
        data = json.loads(body)
        if method.routing_key == 'order_created':
            # Handle Order-Created event
            send_order_created_email(data)
        elif method.routing_key == 'payment_success':
            # Handle Payment-Success event
            send_payment_success_email(data)
        elif method.routing_key == 'payment_failure':
            # Handle Payment-Failure event
            send_payment_failure_email(data)

    channel.basic_consume(queue='order_created', on_message_callback=callback, auto_ack=True)
    channel.basic_consume(queue='payment_success', on_message_callback=callback, auto_ack=True)
    channel.basic_consume(queue='payment_failure', on_message_callback=callback, auto_ack=True)

    channel.start_consuming()


def send_order_created_email(data):
    order_id = data['order_id']
    buyer_email, merchant_email = get_email_addresses(order_id)
    subject = "Order has been created"
    body = f"Order ID: {order_id} has been created."
    if buyer_email:
        send_email(subject, body, buyer_email)
    if merchant_email:
        send_email(subject, body, merchant_email)

def send_payment_success_email(data):
    order_id = data['order_id']
    buyer_email, merchant_email = get_email_addresses(order_id)
    subject = "Order has been purchased"
    body = f"Order {order_id} has been successfully purchased."

    if buyer_email:
        send_email(subject, body, buyer_email)
    if merchant_email:
        send_email(subject, body, merchant_email)

def send_payment_failure_email(data):
    order_id = data['order_id']
    buyer_email, merchant_email = get_email_addresses(order_id)
    subject = "Order purchase failed"
    body = f"Order {order_id} purchase has failed."

    if buyer_email:
        send_email(subject, body, buyer_email)
    if merchant_email:
        send_email(subject, body, merchant_email)

if __name__ == '__main__':
    start_rabbitmq_consumer()