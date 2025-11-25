from flask import Blueprint, jsonify, request
from utils.db import execute_query
import math

bp = Blueprint('mosques', __name__)

@bp.route('/nearby', methods=['GET'])
def get_nearby_mosques():
    """Find mosques within radius of coordinates"""

    try:
        lat = request.args.get('lat')
        lng = request.args.get('lng')

        if lat is None or lng is None:
            return jsonify({"error": "Missing 'lat' or 'lng'"}), 400

        lat = float(lat)
        lng = float(lng)

        radius = float(request.args.get('radius', 10))

        query = """
            SELECT mosque_id, name, address, city, country,
                   latitude, longitude, phone, website,
                   (6371 * acos(
                       cos(radians(%s)) * cos(radians(latitude)) *
                       cos(radians(longitude) - radians(%s)) +
                       sin(radians(%s)) * sin(radians(latitude))
                   )) AS distance
            FROM mosques
            WHERE verified = true
            HAVING distance < %s
            ORDER BY distance
            LIMIT 20
        """

        mosques = execute_query(query, (lat, lng, lat, radius))

        return jsonify({
            'location': {'lat': lat, 'lng': lng},
            'radius_km': radius,
            'count': len(mosques),
            'mosques': mosques
        })

    except ValueError:
        return jsonify({'error': 'Invalid coordinates'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:mosque_id>/prayer-times', methods=['GET'])
def get_mosque_prayer_times(mosque_id):
    """Get congregational prayer times for a mosque"""
    try:
        query = """
            SELECT m.name, m.address, m.city,
                   mpt.prayer_name, mpt.prayer_time, mpt.day_of_week
            FROM mosques m
            JOIN mosque_prayer_times mpt ON m.mosque_id = mpt.mosque_id
            WHERE m.mosque_id = %s
            ORDER BY 
                CASE mpt.prayer_name
                    WHEN 'Fajr' THEN 1
                    WHEN 'Dhuhr' THEN 2
                    WHEN 'Asr' THEN 3
                    WHEN 'Maghrib' THEN 4
                    WHEN 'Isha' THEN 5
                END
        """
        
        results = execute_query(query, (mosque_id,))
        
        if not results:
            return jsonify({'error': 'Mosque not found'}), 404
            
        return jsonify({
            'mosque_id': mosque_id,
            'mosque_info': {
                'name': results[0]['name'],
                'address': results[0]['address'],
                'city': results[0]['city']
            },
            'prayer_times': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500