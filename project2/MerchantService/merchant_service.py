from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
DB_FILE = "merchant_db.txt"

def read_db():
    if not os.path.exists(DB_FILE):
        return {"merchants": {}}
    with open(DB_FILE, "r") as file:
        return json.load(file)

def write_db(data):
    with open(DB_FILE, "w") as file:
        json.dump(data, file, indent=4)

@app.route('/merchants', methods=['POST'])
def create_merchant():
    merchant_data = request.json
    db = read_db()
    merchant_id = max(db['merchants'].keys(), default=0, key=int) + 1
    db['merchants'][merchant_id] = merchant_data
    write_db(db)
    return jsonify({"message": "Merchant created", "merchant_id": merchant_id}), 201

@app.route('/merchants/<int:merchant_id>', methods=['GET'])
def get_merchant(merchant_id):
    db = read_db()
    if str(merchant_id) in db['merchants']:
        return jsonify(db['merchants'][str(merchant_id)]), 200
    return jsonify({"message": "Merchant does not exist"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=8001)