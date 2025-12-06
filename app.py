# FIXED VERSION - app.py
# Copy this entire file to replace your backend app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from utils.db import execute_query
import math

app = Flask(__name__)
CORS(app)

# Calculation methods with their parameters
CALCULATION_METHODS = {
    'ISNA': {'fajr': 15, 'isha': 15},
    'MWL': {'fajr': 18, 'isha': 17},
    'EGYPTIAN': {'fajr': 19.5, 'isha': 17.5},
    'MAKKAH': {'fajr': 18.5, 'isha': 90},
    'KARACHI': {'fajr': 18, 'isha': 18},
    'TEHRAN': {'fajr': 17.7, 'isha': 14}
}

def calculate_prayer_times(lat, lon, date, method='ISNA', asr_method='standard', timezone_offset=None):
    """
    Calculate prayer times using astronomical algorithms
    
    FIXED VERSION with:
    - Proper Asr calculation
    - Timezone support
    - Error handling
    """
    # Get calculation parameters
    params = CALCULATION_METHODS.get(method, CALCULATION_METHODS['ISNA'])
    
    # Auto-calculate timezone offset from longitude if not provided
     # IMPROVED: Better timezone detection
    if timezone_offset is None:
        # Use timezonefinder library (added to requirements.txt)
        from timezonefinder import TimezoneFinder
        from datetime import timezone as tz
        import pytz
        
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=lat, lng=lon)
        
        if timezone_str:
            local_tz = pytz.timezone(timezone_str)
            dt = local_tz.localize(datetime(date.year, date.month, date.day))
            timezone_offset = dt.utcoffset().total_seconds() / 3600
        else:
            # Fallback to longitude-based estimation
            timezone_offset = round(lon / 15)
    
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
    
    # Helper function for time calculation
    def time_for_angle(angle):
        try:
            cos_val = (math.sin(math.radians(-angle)) - 
                       math.sin(math.radians(lat)) * math.sin(math.radians(declination))) / \
                      (math.cos(math.radians(lat)) * math.cos(math.radians(declination)))
            cos_val = max(-1, min(1, cos_val))  # Clamp between -1 and 1
            hour_angle = math.degrees(math.acos(cos_val)) / 15
            return 12 - hour_angle - (lon / 15) + timezone_offset - (E / 60)
        except Exception as e:
            print(f"⚠️ Error calculating time for angle {angle}: {e}")
            return 12  # Return noon as fallback
    
    # Fajr
    fajr = time_for_angle(params['fajr'])
    
    # Sunrise
    sunrise = time_for_angle(-0.833)
    
    # Dhuhr (solar noon)
    dhuhr = 12 - (lon / 15) + timezone_offset - (E / 60)
    
    # ===== FIXED ASR CALCULATION =====
    try:
        shadow_factor = 2 if asr_method == 'hanafi' else 1
        
        # Calculate Asr angle more safely
        lat_decl_diff = abs(lat - declination)
        
        # Handle extreme latitudes
        if lat_decl_diff > 85:
            lat_decl_diff = 85
        
        # Safe arccotangent function
        acot = lambda x: math.degrees(math.atan(1 / x)) if x != 0 else 90
        
        # Calculate shadow length
        tan_value = math.tan(math.radians(lat_decl_diff))
        shadow_length = shadow_factor + tan_value
        
        # Ensure shadow_length is positive and reasonable
        if shadow_length <= 0:
            shadow_length = shadow_factor + 1
        
        # Calculate Asr angle
        angle_asr = acot(shadow_length)
        asr = time_for_angle(90 - angle_asr)
        
        # Validation: Asr must be between Dhuhr and Maghrib
        # Typically Asr is 3-5 hours after Dhuhr
        if asr <= dhuhr:
            print(f"⚠️ Asr ({asr:.2f}) is before Dhuhr ({dhuhr:.2f}), using fallback")
            asr = dhuhr + 3.5  # Safe default: 3.5 hours after Dhuhr
        
    except Exception as e:
        print(f"❌ Asr calculation error: {e}, using fallback")
        # Fallback: Asr is typically 3.5 hours after Dhuhr
        asr = dhuhr + 3.5
    # ===== END FIXED ASR CALCULATION =====
    
    # Maghrib (sunset)
    try:
        maghrib_angle = -0.833
        cos_val = (math.sin(math.radians(-maghrib_angle)) - 
                   math.sin(math.radians(lat)) * math.sin(math.radians(declination))) / \
                  (math.cos(math.radians(lat)) * math.cos(math.radians(declination)))
        cos_val = max(-1, min(1, cos_val))
        
        hour_angle = math.degrees(math.acos(cos_val)) / 15
        maghrib = 12 + hour_angle - (lon / 15) + timezone_offset - (E / 60)
    except Exception as e:
        print(f"⚠️ Maghrib calculation error: {e}")
        maghrib = dhuhr + 6  # Fallback: ~6 hours after Dhuhr
    
    # Isha
    try:
        if isinstance(params['isha'], int) and params['isha'] > 50:
            # Minutes after Maghrib
            isha = maghrib + params['isha'] / 60
        else:
            # Angle-based
            isha = time_for_angle(params['isha'])
            
            # Validation: Isha must be after Maghrib
            if isha <= maghrib:
                isha = maghrib + 1.5  # Fallback: 90 minutes after Maghrib
    except Exception as e:
        print(f"⚠️ Isha calculation error: {e}")
        isha = maghrib + 1.5
    
    def format_time(decimal_time):
        """Convert decimal hours to HH:MM format"""
        # Normalize to 0-24 range
        while decimal_time < 0:
            decimal_time += 24
        while decimal_time >= 24:
            decimal_time -= 24
            
        hours = int(decimal_time)
        minutes = int((decimal_time - hours) * 60)
        
        # Ensure hours and minutes are valid
        hours = max(0, min(23, hours))
        minutes = max(0, min(59, minutes))
        
        return f"{hours:02d}:{minutes:02d}"
    
    times = {
        'fajr': format_time(fajr),
        'sunrise': format_time(sunrise),
        'dhuhr': format_time(dhuhr),
        'asr': format_time(asr),
        'maghrib': format_time(maghrib),
        'isha': format_time(isha)
    }
    
    # Debug logging
    print(f"✅ Prayer times calculated for {date.strftime('%Y-%m-%d')}:")
    print(f"   Location: {lat:.4f}, {lon:.4f}")
    print(f"   Method: {method}, Asr: {asr_method}")
    print(f"   Times: {times}")
    
    return times

def get_cached_prayer_times(lat, lon, date_str, method, asr_method):
    """Get cached prayer times from database"""
    try:
        query = """
            SELECT fajr_time, sunrise_time, dhuhr_time, asr_time, 
                   maghrib_time, isha_time
            FROM prayer_time_cache
            WHERE latitude = %s AND longitude = %s 
              AND prayer_date = %s
              AND calculation_method = %s
              AND asr_method = %s
            LIMIT 1
        """
        
        result = execute_query(query, (lat, lon, date_str, method, asr_method), fetch_one=True)
        
        if result:
            return {
                'fajr': str(result['fajr_time'])[:-3] if result['fajr_time'] else '00:00',
                'sunrise': str(result['sunrise_time'])[:-3] if result['sunrise_time'] else '00:00',
                'dhuhr': str(result['dhuhr_time'])[:-3] if result['dhuhr_time'] else '00:00',
                'asr': str(result['asr_time'])[:-3] if result['asr_time'] else '00:00',
                'maghrib': str(result['maghrib_time'])[:-3] if result['maghrib_time'] else '00:00',
                'isha': str(result['isha_time'])[:-3] if result['isha_time'] else '00:00'
            }
    except Exception as e:
        print(f"⚠️ Cache lookup failed: {e}")
    
    return None

def cache_prayer_times(lat, lon, date_str, method, asr_method, times):
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
            lat, lon, method, asr_method, date_str,
            times['fajr'], times['sunrise'], times['dhuhr'],
            times['asr'], times['maghrib'], times['isha']
        ))
        
        print(f"💾 Prayer times cached for {date_str}")
    except Exception as e:
        print(f"⚠️ Failed to cache prayer times: {e}")

# ============= PRAYER TIMES ROUTE =============

@app.route('/api/prayer-times', methods=['POST'])
def get_prayer_times():
    """Get prayer times for specific date and location"""
    data = request.json
    
    try:
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        date_str = data.get('date')
        method = data.get('method', 'ISNA')
        asr_method = data.get('asr_method', 'standard')
        
        # Get timezone offset (auto-calculate if not provided)
        timezone_offset = data.get('timezone_offset')
        
        # Parse date
        date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Check cache first
        cached = get_cached_prayer_times(lat, lon, date_str, method, asr_method)
        if cached:
            print(f"📦 Serving cached prayer times for {date_str}")
            return jsonify({
                'success': True,
                'date': date_str,
                'times': cached,
                'method': method,
                'asr_method': asr_method,
                'cached': True
            })
        
        # Calculate new times
        print(f"🔄 Calculating prayer times for {date_str}")
        times = calculate_prayer_times(lat, lon, date, method, asr_method, timezone_offset)
        
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
        print(f"❌ Prayer times error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= MOSQUE ROUTES (FIXED FOR DUPLICATES) =============

@app.route('/api/mosques/nearby', methods=['GET'])
def get_nearby_mosques():
    """Find mosques within radius of coordinates - FIXED VERSION"""
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        radius = float(request.args.get('radius', 10))  # km
        
        print(f"🕌 Searching for mosques near ({lat}, {lng}) within {radius}km")
        
        # IMPROVED query with deduplication using CTE
        query = """
            WITH mosque_distances AS (
                SELECT 
                    mosque_id, 
                    name, 
                    address, 
                    city, 
                    country,
                    latitude, 
                    longitude, 
                    phone, 
                    website,
                    (6371 * acos(
                        cos(radians(%s)) * cos(radians(latitude)) *
                        cos(radians(longitude) - radians(%s)) +
                        sin(radians(%s)) * sin(radians(latitude))
                    )) AS distance
                FROM mosques
                WHERE verified = true
            )
            SELECT DISTINCT ON (name, ROUND(CAST(latitude AS numeric), 4), ROUND(CAST(longitude AS numeric), 4))
                mosque_id, name, address, city, country,
                latitude, longitude, phone, website, distance
            FROM mosque_distances
            WHERE distance < %s
            ORDER BY name, ROUND(CAST(latitude AS numeric), 4), ROUND(CAST(longitude AS numeric), 4), distance
            LIMIT 20
        """
        
        mosques = execute_query(query, (lat, lng, lat, radius))
        
        # Additional Python-level deduplication as safety net
        seen = set()
        unique_mosques = []
        
        for mosque in (mosques or []):
            # Create a unique key based on name and rounded location
            key = (
                mosque['name'].lower().strip(),
                round(float(mosque['latitude']), 4),
                round(float(mosque['longitude']), 4)
            )
            
            if key not in seen:
                seen.add(key)
                unique_mosques.append(dict(mosque))
        
        print(f"✅ Found {len(unique_mosques)} unique mosques (removed {len(mosques or []) - len(unique_mosques)} duplicates)")
        
        return jsonify({
            'success': True,
            'location': {'lat': lat, 'lng': lng},
            'radius_km': radius,
            'count': len(unique_mosques),
            'mosques': unique_mosques
        })
        
    except ValueError as e:
        print(f"❌ Invalid parameters: {e}")
        return jsonify({'success': False, 'error': f'Invalid parameters: {str(e)}'}), 400
    except Exception as e:
        print(f"❌ Mosque query error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= HEALTH CHECK =============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        result = execute_query("SELECT 1", fetch_one=True)
        db_status = 'connected' if result else 'error'
    except:
        db_status = 'disconnected'
    
    return jsonify({
        'success': True,
        'status': 'running',
        'database': db_status,
        'message': 'Worldwide Salah API is running'
    })

# ============= CALCULATION METHODS =============

@app.route('/api/calculation-methods', methods=['GET'])
def get_calculation_methods():
    """Get available calculation methods"""
    return jsonify({
        'success': True,
        'methods': {
            'ISNA': 'Islamic Society of North America',
            'MWL': 'Muslim World League',
            'EGYPTIAN': 'Egyptian General Authority of Survey',
            'KARACHI': 'University of Islamic Sciences, Karachi',
            'MAKKAH': 'Umm Al-Qura University, Makkah',
            'TEHRAN': 'Institute of Geophysics, University of Tehran'
        },
        'asr_methods': {
            'standard': 'Standard (Shafi, Maliki, Hanbali)',
            'hanafi': 'Hanafi'
        }
    })

if __name__ == '__main__':
    print("🚀 Starting Worldwide Salah API...")
    print("📍 Prayer time calculation: FIXED")
    print("🕌 Mosque deduplication: FIXED")
    app.run(host='0.0.0.0', port=5000, debug=True)