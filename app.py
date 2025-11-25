from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from config import Config
from utils.db import execute_query
import math
from hijri_converter import Hijri, Gregorian

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
CORS(app)  # Enable CORS for Flutter app
jwt = JWTManager(app)

# Calculation methods with their parameters
CALCULATION_METHODS = {
    'ISNA': {'fajr': 15, 'isha': 15},
    'MWL': {'fajr': 18, 'isha': 17},
    'EGYPTIAN': {'fajr': 19.5, 'isha': 17.5},
    'MAKKAH': {'fajr': 18.5, 'isha': 90},  # 90 means 90 minutes after Maghrib
    'KARACHI': {'fajr': 18, 'isha': 18},
    'TEHRAN': {'fajr': 17.7, 'isha': 14}
}

def calculate_prayer_times(lat, lon, date, method='ISNA', asr_method='standard'):
    """
    Calculate prayer times using astronomical algorithms
    """
    # Get calculation parameters
    params = CALCULATION_METHODS.get(method, CALCULATION_METHODS['ISNA'])
    
    # Calculate Julian date
    year = date.year
    month = date.month
    day = date.day
    
    if month <= 2:
        year -= 1
        month += 12
    
    A = math.floor(year / 100)
    B = 2 - A + math.floor(A / 4)
    JD = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + B - 1524.5
    
    # Calculate equation of time and solar declination
    T = (JD - 2451545.0) / 36525
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
    e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T * T
    C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(math.radians(M))
    C += (0.019993 - 0.000101 * T) * math.sin(math.radians(2 * M))
    C += 0.000289 * math.sin(math.radians(3 * M))
    
    sun_long = L0 + C
    sun_long = sun_long % 360
    
    omega = 125.04 - 1934.136 * T
    lambda_sun = sun_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    epsilon = 23.439291 - 0.0130042 * T
    
    declination = math.degrees(math.asin(math.sin(math.radians(epsilon)) * 
                                         math.sin(math.radians(lambda_sun))))
    
    # Equation of time
    E = 4 * (M - 0.0057183 - L0 + C)
    
    # Calculate prayer times
    timezone_offset = 0  # UTC, adjust in Flutter app
    
    def time_for_angle(angle):
        cos_val = (math.sin(math.radians(-angle)) - 
                   math.sin(math.radians(lat)) * math.sin(math.radians(declination))) / \
                  (math.cos(math.radians(lat)) * math.cos(math.radians(declination)))
        cos_val = max(-1, min(1, cos_val))  # Clamp between -1 and 1
        hour_angle = math.degrees(math.acos(cos_val)) / 15
        return 12 - hour_angle - (lon / 15) + (timezone_offset) - (E / 60)
    
    # Fajr
    fajr = time_for_angle(params['fajr'])
    
    # Sunrise (sun's center at horizon with 0.833 degrees for refraction)
    sunrise = time_for_angle(-0.833)
    
    # Dhuhr (solar noon)
    dhuhr = 12 - (lon / 15) + timezone_offset - (E / 60)
    
    # Asr
    # Standard: shadow length = object length + noon shadow
    # Hanafi: shadow length = 2 * object length + noon shadow
    shadow_factor = 2 if asr_method == 'hanafi' else 1
    
    acot = lambda x: math.degrees(math.atan(1 / x))
    angle_asr = acot(shadow_factor + math.tan(math.radians(abs(lat - declination))))
    asr = time_for_angle(90 - angle_asr)
    
    # Maghrib (sunset)
    maghrib = time_for_angle(-0.833)
    maghrib = 12 + (lon / 15) - timezone_offset + (E / 60) + \
              math.degrees(math.acos((math.sin(math.radians(-0.833)) - 
                                     math.sin(math.radians(lat)) * math.sin(math.radians(declination))) / 
                                    (math.cos(math.radians(lat)) * math.cos(math.radians(declination))))) / 15
    
    # Isha
    if isinstance(params['isha'], int) and params['isha'] > 50:
        # Minutes after Maghrib
        isha = maghrib + params['isha'] / 60
    else:
        # Angle-based
        isha = time_for_angle(params['isha'])
    
    def format_time(decimal_time):
        hours = int(decimal_time)
        minutes = int((decimal_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    return {
        'fajr': format_time(fajr),
        'sunrise': format_time(sunrise),
        'dhuhr': format_time(dhuhr),
        'asr': format_time(asr),
        'maghrib': format_time(maghrib),
        'isha': format_time(isha)
    }

def cache_prayer_times(lat, lon, date, method, asr_method, times):
    """Cache calculated prayer times to database"""
    try:
        query = """
            INSERT INTO prayer_time_cache 
            (latitude, longitude, calculation_method, asr_method, prayer_date,
             fajr_time, sunrise_time, dhuhr_time, asr_time, maghrib_time, isha_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (latitude, longitude, calculation_method, asr_method, prayer_date)
            DO UPDATE SET
                fajr_time = EXCLUDED.fajr_time,
                sunrise_time = EXCLUDED.sunrise_time,
                dhuhr_time = EXCLUDED.dhuhr_time,
                asr_time = EXCLUDED.asr_time,
                maghrib_time = EXCLUDED.maghrib_time,
                isha_time = EXCLUDED.isha_time
        """
        execute_query(query, (
            lat, lon, method, asr_method, date,
            times['fajr'], times['sunrise'], times['dhuhr'],
            times['asr'], times['maghrib'], times['isha']
        ))
    except Exception as e:
        print(f"Cache error: {e}")

def get_cached_prayer_times(lat, lon, date, method, asr_method):
    """Get prayer times from cache"""
    try:
        query = """
            SELECT fajr_time, sunrise_time, dhuhr_time, asr_time, 
                   maghrib_time, isha_time
            FROM prayer_time_cache
            WHERE latitude = %s AND longitude = %s 
              AND prayer_date = %s
              AND calculation_method = %s
              AND asr_method = %s
        """
        result = execute_query(query, (lat, lon, date, method, asr_method), fetch_one=True)
        
        if result:
            # Convert time objects to strings
            return {
                'fajr': str(result['fajr_time']),
                'sunrise': str(result['sunrise_time']),
                'dhuhr': str(result['dhuhr_time']),
                'asr': str(result['asr_time']),
                'maghrib': str(result['maghrib_time']),
                'isha': str(result['isha_time'])
            }
        return None
    except Exception as e:
        print(f"Cache retrieval error: {e}")
        return None

# ============= AUTHENTICATION ROUTES =============

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
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
        pref_query = "INSERT INTO user_preferences (user_id) VALUES (%s)"
        execute_query(pref_query, (result['user_id'],))
        
        # Generate JWT token
        access_token = create_access_token(identity=result['user_id'])
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': dict(result),
            'access_token': access_token
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
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
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        # Generate JWT token
        access_token = create_access_token(identity=user['user_id'])
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'user_id': user['user_id'],
                'email': user['email'],
                'full_name': user['full_name']
            },
            'access_token': access_token
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= PRAYER TIME ROUTES =============

@app.route('/api/prayer-times', methods=['POST'])
def get_prayer_times():
    """Get prayer times for a specific location and date"""
    data = request.json
    
    try:
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        method = data.get('method', 'ISNA')
        asr_method = data.get('asr_method', 'standard')
        
        date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Try to get from cache first
        cached_times = get_cached_prayer_times(lat, lon, date_str, method, asr_method)
        
        if cached_times:
            return jsonify({
                'success': True,
                'date': date_str,
                'times': cached_times,
                'method': method,
                'asr_method': asr_method,
                'cached': True
            })
        
        # Calculate if not cached
        times = calculate_prayer_times(lat, lon, date, method, asr_method)
        
        # Cache the results
        cache_prayer_times(lat, lon, date_str, method, asr_method, times)
        
        return jsonify({
            'success': True,
            'date': date_str,
            'times': times,
            'method': method,
            'asr_method': asr_method,
            'cached': False
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/monthly-prayers', methods=['POST'])
def get_monthly_prayers():
    """Get prayer times for entire month"""
    data = request.json
    
    try:
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        year = int(data.get('year', datetime.now().year))
        month = int(data.get('month', datetime.now().month))
        method = data.get('method', 'ISNA')
        asr_method = data.get('asr_method', 'standard')
        
        # Get number of days in month
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        days_in_month = (next_month - datetime(year, month, 1)).days
        
        monthly_times = []
        for day in range(1, days_in_month + 1):
            date = datetime(year, month, day)
            date_str = date.strftime('%Y-%m-%d')
            
            # Try cache first
            cached = get_cached_prayer_times(lat, lon, date_str, method, asr_method)
            
            if cached:
                times = cached
            else:
                times = calculate_prayer_times(lat, lon, date, method, asr_method)
                cache_prayer_times(lat, lon, date_str, method, asr_method, times)
            
            monthly_times.append({
                'date': date_str,
                'day': day,
                'times': times
            })
        
        return jsonify({
            'success': True,
            'year': year,
            'month': month,
            'prayers': monthly_times
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= MOSQUE ROUTES =============

@app.route('/api/mosques/nearby', methods=['GET'])
def get_nearby_mosques():
    """Find mosques within radius of coordinates"""
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        radius = float(request.args.get('radius', 10))  # km
        
        # Fixed query - use subquery to properly filter by calculated distance
        query = """
            SELECT * FROM (
                SELECT mosque_id, name, address, city, country,
                       latitude, longitude, phone, website,
                       (6371 * acos(
                           cos(radians(%s)) * cos(radians(latitude)) *
                           cos(radians(longitude) - radians(%s)) +
                           sin(radians(%s)) * sin(radians(latitude))
                       )) AS distance
                FROM mosques
                WHERE verified = true
            ) AS mosques_with_distance
            WHERE distance < %s
            ORDER BY distance
            LIMIT 20
        """
        
        mosques = execute_query(query, (lat, lng, lat, radius))
        
        # Handle case where no mosques found
        mosque_list = []
        if mosques:
            mosque_list = [dict(m) for m in mosques]
        
        return jsonify({
            'success': True,
            'location': {'lat': lat, 'lng': lng},
            'radius_km': radius,
            'count': len(mosque_list),
            'mosques': mosque_list
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid parameters: {str(e)}'}), 400
    except Exception as e:
        print(f"❌ Mosque query error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/mosques/<int:mosque_id>/prayer-times', methods=['GET'])
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
            return jsonify({'success': False, 'error': 'Mosque not found'}), 404
            
        return jsonify({
            'success': True,
            'mosque_id': mosque_id,
            'mosque_info': {
                'name': results[0]['name'],
                'address': results[0]['address'],
                'city': results[0]['city']
            },
            'prayer_times': [dict(r) for r in results]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= RAMADAN ROUTES =============

@app.route('/api/ramadan', methods=['POST'])
def get_ramadan_info():
    """Get Ramadan start/end dates and fasting times"""
    data = request.json
    
    try:
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        year = int(data.get('year', datetime.now().year))
        method = data.get('method', 'ISNA')
        
        # Check database for Ramadan dates first
        query = "SELECT start_date, end_date FROM ramadan_dates WHERE gregorian_year = %s"
        ramadan_info = execute_query(query, (year,), fetch_one=True)
        
        if ramadan_info:
            start_date = ramadan_info['start_date']
            end_date = ramadan_info['end_date']
        else:
            # Fallback calculation
            hijri_start = Hijri(year - 621, 9, 1)
            greg_start = hijri_start.to_gregorian()
            start_date = datetime(greg_start.year, greg_start.month, greg_start.day)
            end_date = start_date + timedelta(days=29)
        
        # Calculate fasting times for each day
        ramadan_days = []
        current_date = start_date if isinstance(start_date, datetime) else datetime.combine(start_date, datetime.min.time())
        end_date_obj = end_date if isinstance(end_date, datetime) else datetime.combine(end_date, datetime.min.time())
        
        while current_date <= end_date_obj:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Get or calculate prayer times
            cached = get_cached_prayer_times(lat, lon, date_str, method, 'standard')
            if cached:
                times = cached
            else:
                times = calculate_prayer_times(lat, lon, current_date, method, 'standard')
                cache_prayer_times(lat, lon, date_str, method, 'standard', times)
            
            ramadan_days.append({
                'date': date_str,
                'day': len(ramadan_days) + 1,
                'suhoor_end': times['fajr'],
                'iftar': times['maghrib']
            })
            
            current_date += timedelta(days=1)
        
        return jsonify({
            'success': True,
            'year': year,
            'start_date': ramadan_days[0]['date'] if ramadan_days else None,
            'end_date': ramadan_days[-1]['date'] if ramadan_days else None,
            'fasting_schedule': ramadan_days
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= QIBLA ROUTE =============

@app.route('/api/qibla', methods=['POST'])
def get_qibla_direction():
    """Calculate Qibla direction from user's location"""
    data = request.json
    
    try:
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        
        # Kaaba coordinates
        kaaba_lat = 21.4225
        kaaba_lon = 39.8262
        
        # Convert to radians
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        kaaba_lat_rad = math.radians(kaaba_lat)
        kaaba_lon_rad = math.radians(kaaba_lon)
        
        # Calculate bearing
        dLon = kaaba_lon_rad - lon_rad
        y = math.sin(dLon) * math.cos(kaaba_lat_rad)
        x = math.cos(lat_rad) * math.sin(kaaba_lat_rad) - \
            math.sin(lat_rad) * math.cos(kaaba_lat_rad) * math.cos(dLon)
        
        bearing = math.degrees(math.atan2(y, x))
        qibla_direction = (bearing + 360) % 360
        
        return jsonify({
            'success': True,
            'qibla_direction': round(qibla_direction, 2),
            'latitude': lat,
            'longitude': lon
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= USER PREFERENCES ROUTES =============

@app.route('/api/user/preferences', methods=['GET'])
@jwt_required()
def get_user_preferences():
    """Get user preferences"""
    try:
        user_id = get_jwt_identity()
        
        query = """
            SELECT calculation_method, asr_method, theme, language,
                   notifications_enabled, adhan_enabled
            FROM user_preferences
            WHERE user_id = %s
        """
        prefs = execute_query(query, (user_id,), fetch_one=True)
        
        if not prefs:
            return jsonify({'success': False, 'error': 'Preferences not found'}), 404
        
        return jsonify({
            'success': True,
            'preferences': dict(prefs)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/preferences', methods=['PUT'])
@jwt_required()
def update_user_preferences():
    """Update user preferences"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        query = """
            UPDATE user_preferences
            SET calculation_method = COALESCE(%s, calculation_method),
                asr_method = COALESCE(%s, asr_method),
                theme = COALESCE(%s, theme),
                language = COALESCE(%s, language),
                notifications_enabled = COALESCE(%s, notifications_enabled),
                adhan_enabled = COALESCE(%s, adhan_enabled)
            WHERE user_id = %s
        """
        
        execute_query(query, (
            data.get('calculation_method'),
            data.get('asr_method'),
            data.get('theme'),
            data.get('language'),
            data.get('notifications_enabled'),
            data.get('adhan_enabled'),
            user_id
        ))
        
        return jsonify({
            'success': True,
            'message': 'Preferences updated successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= UTILITY ROUTES =============

@app.route('/api/calculation-methods', methods=['GET'])
def get_calculation_methods():
    """Return available calculation methods"""
    methods = {
        name: {
            'fajr_angle': params['fajr'],
            'isha_angle': params['isha']
        }
        for name, params in CALCULATION_METHODS.items()
    }
    
    return jsonify({
        'success': True,
        'methods': methods
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        execute_query("SELECT 1", fetch_one=True)
        db_status = 'connected'
    except:
        db_status = 'disconnected'
    
    return jsonify({
        'success': True,
        'status': 'running',
        'database': db_status,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)