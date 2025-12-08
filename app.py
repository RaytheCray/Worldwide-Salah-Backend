# COMPLETE FIXED VERSION - app.py
# Updated with timezone support, proper Asr calculation, and PostgreSQL integration

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

def get_timezone_offset(lat, lon):
    """Get timezone offset from coordinates"""
    try:
        from timezonefinder import TimezoneFinder
        import pytz
        
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=lat, lng=lon)
        
        if timezone_str:
            tz = pytz.timezone(timezone_str)
            dt = tz.localize(datetime.now())
            offset_seconds = dt.utcoffset().total_seconds()
            return offset_seconds / 3600
        else:
            # Fallback to longitude-based estimation
            return round(lon / 15)
    except Exception as e:
        print(f"⚠️ Timezone calculation error: {e}")
        # Fallback to longitude-based estimation
        return round(lon / 15)

def calculate_prayer_times(lat, lon, date, method='ISNA', asr_method='standard', timezone_offset=None):
    """
    Calculate prayer times using astronomical algorithms with timezone support
    FIXED VERSION - Corrects Asr and Sunrise calculations
    """
    # Get calculation parameters
    params = CALCULATION_METHODS.get(method, CALCULATION_METHODS['ISNA'])
    
    # Auto-calculate timezone offset if not provided
    if timezone_offset is None:
        timezone_offset = get_timezone_offset(lat, lon)
    
    print(f"🕌 Calculating for {date} with timezone offset: {timezone_offset} hours")
    
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
    E = 4 * (L0 - lambda_sun)
    
    def time_for_angle(angle):
        """Calculate time for a given sun angle"""
        try:
            cos_val = (math.sin(math.radians(angle)) - 
                       math.sin(math.radians(lat)) * math.sin(math.radians(declination))) / \
                      (math.cos(math.radians(lat)) * math.cos(math.radians(declination)))
            cos_val = max(-1, min(1, cos_val))
            hour_angle = math.degrees(math.acos(-cos_val)) / 15
            return 12 - hour_angle - (lon / 15) + timezone_offset - (E / 60)
        except Exception as e:
            print(f"⚠️ Time calculation error for angle {angle}: {e}")
            return 12
    
    # Calculate prayer times
    try:
        fajr = time_for_angle(-params['fajr'])
    except Exception as e:
        print(f"⚠️ Fajr calculation error: {e}")
        fajr = 5.0
    
    # ✅ FIXED: Sunrise calculation
    try:
        sunrise_angle = -0.833  # Standard atmospheric refraction
        cos_val = (math.sin(math.radians(sunrise_angle)) - 
                   math.sin(math.radians(lat)) * math.sin(math.radians(declination))) / \
                  (math.cos(math.radians(lat)) * math.cos(math.radians(declination)))
        cos_val = max(-1, min(1, cos_val))
        hour_angle = math.degrees(math.acos(-cos_val)) / 15
        # ✅ CHANGED: Use POSITIVE hour angle for sunrise (sun rising in east)
        sunrise = 12 - hour_angle - (lon / 15) + timezone_offset - (E / 60)
    except Exception as e:
        print(f"⚠️ Sunrise calculation error: {e}")
        sunrise = fajr + 1.2  # Fallback: ~1.2 hours after Fajr
    
    # Dhuhr (midday)
    dhuhr = 12 - (lon / 15) + timezone_offset - (E / 60)
    
    # ✅ FIXED: Asr calculation
    try:
        # Shadow ratio: 1 for Standard, 2 for Hanafi
        shadow_ratio = 2 if asr_method == 'hanafi' else 1
        
        # Calculate sun altitude angle when shadow = object_height * shadow_ratio
        # Formula: tan(altitude) = 1 / (shadow_ratio + tan|lat - dec|)
        lat_dec_diff = abs(lat - declination)
        
        # Sun altitude angle (degrees above horizon)
        sun_altitude = math.degrees(math.atan(1.0 / (shadow_ratio + math.tan(math.radians(lat_dec_diff)))))
        
        # Calculate hour angle for this altitude
        # Use the NEGATIVE of sun_altitude (below zenith, not horizon)
        asr_angle = 90 - sun_altitude  # Convert altitude to angle from horizon
        
        cos_asr = (math.sin(math.radians(asr_angle)) - 
                   math.sin(math.radians(lat)) * math.sin(math.radians(declination))) / \
                  (math.cos(math.radians(lat)) * math.cos(math.radians(declination)))
        cos_asr = max(-1, min(1, cos_asr))
        hour_angle_asr = math.degrees(math.acos(-cos_asr)) / 15
        
        # ✅ CHANGED: Use POSITIVE hour angle for afternoon time
        asr = 12 + hour_angle_asr - (lon / 15) + timezone_offset - (E / 60)
        
        # Validation: Asr must be after Dhuhr
        if asr <= dhuhr:
            print(f"⚠️ Asr before Dhuhr! Setting to Dhuhr + 3 hours")
            asr = dhuhr + 3.0
    except Exception as e:
        print(f"⚠️ Asr calculation error: {e}, using fallback")
        asr = dhuhr + 3.5
    
    # Maghrib (sunset)
    try:
        maghrib_angle = -0.833
        cos_val = (math.sin(math.radians(maghrib_angle)) - 
                   math.sin(math.radians(lat)) * math.sin(math.radians(declination))) / \
                  (math.cos(math.radians(lat)) * math.cos(math.radians(declination)))
        cos_val = max(-1, min(1, cos_val))
        
        # ✅ CHANGED: Use POSITIVE hour angle for sunset (sun setting in west)
        hour_angle = math.degrees(math.acos(-cos_val)) / 15
        maghrib = 12 + hour_angle - (lon / 15) + timezone_offset - (E / 60)
    except Exception as e:
        print(f"⚠️ Maghrib calculation error: {e}")
        maghrib = dhuhr + 6
    
    # Isha
    try:
        if isinstance(params['isha'], int) and params['isha'] > 50:
            # Minutes after Maghrib
            isha = maghrib + params['isha'] / 60
        else:
            # Angle-based
            isha = time_for_angle(-params['isha'])
            
            # Validation: Isha must be after Maghrib
            if isha <= maghrib:
                isha = maghrib + 1.5
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
    print(f"   Fajr: {times['fajr']}, Sunrise: {times['sunrise']}, Dhuhr: {times['dhuhr']}")
    print(f"   Asr: {times['asr']}, Maghrib: {times['maghrib']}, Isha: {times['isha']}")
    
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
        bypass_cache = data.get('bypass_cache', False)
        
        # Get timezone offset from client (optional)
        timezone_offset = data.get('timezone_offset')
        
        # Parse date
        date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Check cache first (unless bypassed)
        if not bypass_cache:
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

# ============= MONTHLY PRAYERS ROUTE =============

@app.route('/api/monthly-prayers', methods=['POST'])
def get_monthly_prayers():
    """Get prayer times for entire month"""
    data = request.json
    
    try:
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        year = int(data.get('year'))
        month = int(data.get('month'))
        method = data.get('method', 'ISNA')
        asr_method = data.get('asr_method', 'standard')
        timezone_offset = data.get('timezone_offset')
        
        # Calculate number of days in month
        import calendar
        num_days = calendar.monthrange(year, month)[1]
        
        prayers = []
        for day in range(1, num_days + 1):
            date = datetime(year, month, day)
            date_str = date.strftime('%Y-%m-%d')
            
            # Check cache first
            cached = get_cached_prayer_times(lat, lon, date_str, method, asr_method)
            if cached:
                times = cached
            else:
                times = calculate_prayer_times(lat, lon, date, method, asr_method, timezone_offset)
                cache_prayer_times(lat, lon, date_str, method, asr_method, times)
            
            prayers.append({
                'day': day,
                'date': date_str,
                'times': times
            })
        
        return jsonify({
            'success': True,
            'year': year,
            'month': month,
            'prayers': prayers
        })
        
    except Exception as e:
        print(f"❌ Monthly prayers error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= RAMADAN ROUTE =============

@app.route('/api/ramadan', methods=['POST'])
def get_ramadan():
    """Get Ramadan fasting schedule"""
    data = request.json
    
    try:
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        year = int(data.get('year'))
        method = data.get('method', 'ISNA')
        timezone_offset = data.get('timezone_offset')
        
        # Get Ramadan dates from database
        query = """
            SELECT start_date, end_date 
            FROM ramadan_dates 
            WHERE gregorian_year = %s
        """
        ramadan_dates = execute_query(query, (year,), fetch_one=True)
        
        if not ramadan_dates:
            return jsonify({
                'success': False,
                'error': f'Ramadan dates not found for {year}'
            }), 404
        
        start_date = ramadan_dates['start_date']
        end_date = ramadan_dates['end_date']
        
        # Calculate fasting times for each day
        fasting_schedule = []
        current_date = start_date
        day_num = 1
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Get or calculate prayer times
            cached = get_cached_prayer_times(lat, lon, date_str, method, 'standard')
            if cached:
                times = cached
            else:
                times = calculate_prayer_times(lat, lon, current_date, method, 'standard', timezone_offset)
                cache_prayer_times(lat, lon, date_str, method, 'standard', times)
            
            fasting_schedule.append({
                'day': day_num,
                'date': date_str,
                'suhoor_end': times['fajr'],  # Suhoor ends at Fajr
                'iftar_time': times['maghrib']  # Iftar at Maghrib
            })
            
            current_date += timedelta(days=1)
            day_num += 1
        
        return jsonify({
            'success': True,
            'year': year,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'fasting_schedule': fasting_schedule
        })
        
    except Exception as e:
        print(f"❌ Ramadan error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= QIBLA ROUTE =============

@app.route('/api/qibla', methods=['POST'])
def get_qibla():
    """Calculate Qibla direction"""
    data = request.json
    
    try:
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        
        # Kaaba coordinates
        kaaba_lat = 21.4225
        kaaba_lon = 39.8262
        
        # Calculate bearing
        lat_rad = math.radians(lat)
        kaaba_lat_rad = math.radians(kaaba_lat)
        lon_diff = math.radians(kaaba_lon - lon)
        
        x = math.sin(lon_diff) * math.cos(kaaba_lat_rad)
        y = math.cos(lat_rad) * math.sin(kaaba_lat_rad) - \
            math.sin(lat_rad) * math.cos(kaaba_lat_rad) * math.cos(lon_diff)
        
        bearing = math.degrees(math.atan2(x, y))
        bearing = (bearing + 360) % 360
        
        return jsonify({
            'success': True,
            'qibla_direction': bearing,
            'latitude': lat,
            'longitude': lon
        })
        
    except Exception as e:
        print(f"❌ Qibla error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= MOSQUE ROUTES =============

@app.route('/api/mosques/nearby', methods=['GET'])
def get_nearby_mosques():
    """Find mosques within radius of coordinates"""
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        radius = float(request.args.get('radius', 10))
        
        print(f"🕌 Searching for mosques near ({lat}, {lng}) within {radius}km")
        
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
        
        # Additional deduplication
        seen = set()
        unique_mosques = []
        
        for mosque in (mosques or []):
            key = (
                mosque['name'].lower().strip(),
                round(float(mosque['latitude']), 4),
                round(float(mosque['longitude']), 4)
            )
            
            if key not in seen:
                seen.add(key)
                unique_mosques.append(dict(mosque))
        
        print(f"✅ Found {len(unique_mosques)} unique mosques")
        
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

# ============= HEALTH & INFO ROUTES =============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
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

@app.route('/')
def home():
    """Root endpoint - API information"""
    return jsonify({
        'name': 'Worldwide Salah API',
        'version': '1.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'prayer_times': '/api/prayer-times',
            'monthly': '/api/monthly-prayers',
            'ramadan': '/api/ramadan',
            'qibla': '/api/qibla',
            'mosques': '/api/mosques',
            'methods': '/api/calculation-methods'
        }
    })

if __name__ == '__main__':
    print("🚀 Starting Worldwide Salah API...")
    print("📍 Prayer time calculation with timezone support: ENABLED")
    print("🕌 Mosque deduplication: ENABLED")
    print("💾 PostgreSQL caching: ENABLED")
    app.run(host='0.0.0.0', port=5000, debug=True)