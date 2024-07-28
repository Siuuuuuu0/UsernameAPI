from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pybloom_live import BloomFilter
from dotenv import load_dotenv
import random
import string
import os

load_dotenv()

app = Flask(__name__)

# Подключение к MongoDB
client = MongoClient(os.getenv('DATABASE_URI'))
def check_connection(client):
    try:
        client.admin.command('ping')
        print("Connection to MongoDB is alive")
        return True
    except ConnectionFailure:
        print("Connection to MongoDB failed")
        return False


if check_connection(client):
    db = client['AuthPageDB']
    users_collection = db['users']

# Класс для маштабирования фильтра в зависимости от количества никнеймов
class MultiBloomFilter:
    def __init__(self, initial_capacity, error_rate):
        self.filters = [BloomFilter(capacity=initial_capacity, error_rate=error_rate)]
    
    def add(self, item):
        # Если первый фильтр переполнен, добавляем новый
        if not self.filters[0].add(item):
            self.filters.append(BloomFilter(capacity=len(self.filters[0]), error_rate=0.001))
            self.filters[-1].add(item)
    
    def __contains__(self, item):
        # Проверяем все фильтры
        return any(item in bloom_filter for bloom_filter in self.filters)


# Инициализация Bloom фильтра
bloom_filter = MultiBloomFilter(initial_capacity=10000, error_rate=0.001)

# added_nicknames = []

# Заполнение Bloom фильтра существующими никнеймами
existing_usernames = users_collection.distinct('username')
for username in existing_usernames:
    print(username)
    bloom_filter.add(username)
    # added_usernames.append(username)

def generate_custom_username(first_name, last_name):
    base_username = (first_name[:2] + last_name[:2]).lower()
    numbers = ''.join(random.choices(string.digits, k=3))
    special_chars = ''.join(random.choices('!#$%^&*', k=2))
    return base_username + numbers + special_chars

def is_username_unique(username):
    # if username in bloom_filter:
    #     return users_collection.find_one({"username": username}) is None
    # return True
    return username in bloom_filter

@app.route('/generate_username', methods=['POST'])
def generate_username_endpoint():
    data = request.get_json()
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    if not first_name or not last_name:
        return jsonify({'error': 'Invalid input'}), 400
    
    username = generate_custom_username(first_name, last_name)
    while not is_username_unique(username):
        username = generate_custom_username(first_name, last_name)
    
    return jsonify({'username': username}), 200

@app.route('/add_username', methods=['POST'])
def add_username_endpoint():
    data = request.get_json()
    username = data.get('username')
    if not username : 
        return jsonify({'error' : 'no username provided'}), 400
    bloom_filter.add(username)
    # added_usernames.append(username)
    # for username in added_usernames:
    #     print(username)
    return jsonify({'success': 'username' }), 204

if __name__ == '__main__':
    app.run(debug=True)
