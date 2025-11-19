from flask import Blueprint, jsonify, request
from utils.db import execute_query
from datetime import datetime

bp = Blueprint('prayer_times', __name__)

@bp.route('/', methods=['GET'])
def get_prayer_times():
    """Get prayer times for a location and date"""
    try:
        # Get query parameters
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        method = request.args.get('method', 'ISNA')
        asr_method = request.args.get('asr_method', 'Standard')
        
        # Check cache first
        query = """
            SELECT fajr_time, sunrise_time, dhuhr_time, asr_time, 
                   maghrib_time, isha_time
            FROM prayer_time_cache
            WHERE latitude = %s AND longitude = %s 
              AND prayer_date = %s
              AND calculation_method = %s
              AND asr_method = %s
        """
        
        result = execute_query(
            query, 
            (lat, lng, date, method, asr_method),
            fetch_one=True
        )
        
        if result:
            return jsonify({
                'date': date,
                'location': {'lat': lat, 'lng': lng},
                'prayer_times': result,
                'cached': True
            })
        else:
            # TODO: Calculate prayer times and cache them
            # For now, return mock data
            return jsonify({
                'error': 'Prayer times not cached. Implement calculation.'
            }), 404
            
    except ValueError:
        return jsonify({'error': 'Invalid coordinates'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/month', methods=['GET'])
def get_monthly_prayer_times():
    """Get prayer times for entire month"""
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))
        
        query = """
            SELECT prayer_date, fajr_time, sunrise_time, dhuhr_time, 
                   asr_time, maghrib_time, isha_time
            FROM prayer_time_cache
            WHERE latitude = %s AND longitude = %s
              AND EXTRACT(YEAR FROM prayer_date) = %s
              AND EXTRACT(MONTH FROM prayer_date) = %s
            ORDER BY prayer_date
        """
        
        results = execute_query(query, (lat, lng, year, month))
        
        return jsonify({
            'year': year,
            'month': month,
            'prayer_times': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500