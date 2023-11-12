from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
DB_FILE = "buyer_db.txt"

def read_db():
    if not os.path.exists(DB_FILE):
        return {"buyers": {}}
    with open(DB_FILE, "r") as file:
        return json.load(file)

def write_db(data):
    with open(DB_FILE, "w") as file:
        json.dump(data, file, indent=4)

@app.route('/buyers', methods=['POST'])
def create_buyer():
    buyer_data = request.json
    db = read_db()
    buyer_id = max(db['buyers'].keys(), default=0, key=int) + 1
    db['buyers'][buyer_id] = buyer_data
    write_db(db)
    return jsonify({"message": "Buyer created", "buyer_id": buyer_id}), 201

@app.route('/buyers/<int:buyer_id>', methods=['GET'])
def get_buyer(buyer_id):
    db = read_db()
    if str(buyer_id) in db['buyers']:
        return jsonify(db['buyers'][str(buyer_id)]), 200
    return jsonify({"message": "Buyer does not exist"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=8002)