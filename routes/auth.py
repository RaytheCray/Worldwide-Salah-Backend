from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import execute_query

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # Insert user
        query = """
            INSERT INTO users (email, password_hash, full_name)
            VALUES (%s, %s, %s)
            RETURNING user_id, email, full_name
        """
        
        result = execute_query(query, (email, password_hash, full_name), fetch_one=True)
        
        # Create default preferences
        pref_query = """
            INSERT INTO user_preferences (user_id)
            VALUES (%s)
        """
        execute_query(pref_query, (result['user_id'],))
        
        # Generate JWT token
        access_token = create_access_token(identity=result['user_id'])
        
        return jsonify({
            'message': 'User created successfully',
            'user': result,
            'access_token': access_token
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        # Get user
        query = "SELECT user_id, email, password_hash, full_name FROM users WHERE email = %s"
        user = execute_query(query, (email,), fetch_one=True)
        
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate JWT token
        access_token = create_access_token(identity=user['user_id'])
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'user_id': user['user_id'],
                'email': user['email'],
                'full_name': user['full_name']
            },
            'access_token': access_token
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500