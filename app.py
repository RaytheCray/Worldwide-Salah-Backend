# Using praytimes library

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from utils.db import execute_query
import math

app = Flask(__name__)
CORS(app)

# Install: pip install praytimes
try:
    from praytimes import PrayTimes
    PRAYTIMES_AVAILABLE = True
    print("✅ PrayTimes library loaded successfully")
except ImportError:
    PRAYTIMES_AVAILABLE = False
    print("⚠️ PrayTimes library not found. Please install: pip install praytimes")

# Calculation methods mapping
CALCULATION_METHODS = {
    'ISNA': 'ISNA',
    'MWL': 'MWL',
    'EGYPTIAN': 'Egypt',
    'KARACHI': 'Karachi',
    'MAKKAH': 'Makkah',
    'TEHRAN': 'Tehran'
}

def calculate_prayer_times_with_praytimes(lat, lon, date, method='ISNA', asr_method='standard'):
    """
    Calculate prayer times using the praytimes library
    """
    try:
        # Create PrayTimes object
        pt = PrayTimes()
        
        # Set calculation method
        method_name = CALCULATION_METHODS.get(method, 'ISNA')
        pt.setMethod(method_name)
        
        # Set Asr calculation method
        if asr_method == 'hanafi':
            pt.adjust({'asr': 'Hanafi'})
        else:
            pt.adjust({'asr': 'Standard'})
        
        # Get timezone offset (in hours)
        # Using the date's timezone offset
        import pytz
        from timezonefinder import TimezoneFinder
        
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=lat, lng=lon)
        
        if timezone_str:
            tz = pytz.timezone(timezone_str)
            dt = tz.localize(datetime(date.year, date.month, date.day))
            timezone_offset = dt.utcoffset().total_seconds() / 3600
        else:
            # Fallback to approximate timezone
            timezone_offset = round(lon / 15)
        
        # Calculate prayer times
        # praytimes expects: (year, month, day, latitude, longitude, timezone)
        times = pt.getTimes(
            (date.year, date.month, date.day),
            (lat, lon),
            timezone_offset
        )
        
        # Format times (praytimes returns 24-hour format like "05:53")
        formatted_times = {
            'fajr': times['fajr'],
            'sunrise': times['sunrise'],
            'dhuhr': times['dhuhr'],
            'asr': times['asr'],
            'maghrib': times['maghrib'],
            'isha': times['isha']
        }
        
        print(f"✅ Prayer times calculated with praytimes library:")
        print(f"   Location: {lat:.4f}, {lon:.4f}")
        print(f"   Date: {date.strftime('%Y-%m-%d')}")
        print(f"   Method: {method}, Asr: {asr_method}")
        print(f"   Fajr: {formatted_times['fajr']}, Sunrise: {formatted_times['sunrise']}, Dhuhr: {formatted_times['dhuhr']}")
        print(f"   Asr: {formatted_times['asr']}, Maghrib: {formatted_times['maghrib']}, Isha: {formatted_times['isha']}")
        
        return formatted_times
        
    except Exception as e:
        print(f"❌ PrayTimes calculation error: {e}")
        import traceback
        traceback.print_exc()
        raise

def get_cached_prayer_times(lat, lon, date_str, method, asr_method):
    """Get cached prayer times from database"""
    try:
        # Round coordinates to 4 decimal places for cache matching
        lat = round(lat, 4)
        lon = round(lon, 4)
        
        query = """
            SELECT fajr_time, sunrise_time, dhuhr_time, asr_time, 
                   maghrib_time, isha_time
            FROM prayer_time_cache
            WHERE ROUND(CAST(latitude AS numeric), 4) = %s 
              AND ROUND(CAST(longitude AS numeric), 4) = %s 
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
        # Round coordinates to 4 decimal places
        lat = round(lat, 4)
        lon = round(lon, 4)
        
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
        if not PRAYTIMES_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'PrayTimes library not installed. Run: pip install praytimes'
            }), 500
        
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        date_str = data.get('date')
        method = data.get('method', 'ISNA')
        asr_method = data.get('asr_method', 'standard')
        bypass_cache = data.get('bypass_cache', False)
        
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
        
        # Calculate new times using praytimes library
        print(f"🔄 Calculating prayer times with praytimes for {date_str}")
        times = calculate_prayer_times_with_praytimes(lat, lon, date, method, asr_method)
        
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
        if not PRAYTIMES_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'PrayTimes library not installed'
            }), 500
        
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        year = int(data.get('year'))
        month = int(data.get('month'))
        method = data.get('method', 'ISNA')
        asr_method = data.get('asr_method', 'standard')
        
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
                times = calculate_prayer_times_with_praytimes(lat, lon, date, method, asr_method)
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
        if not PRAYTIMES_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'PrayTimes library not installed'
            }), 500
        
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        year = int(data.get('year'))
        method = data.get('method', 'ISNA')
        
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
            
            # Get prayer times
            cached = get_cached_prayer_times(lat, lon, date_str, method, 'standard')
            if cached:
                times = cached
            else:
                times = calculate_prayer_times_with_praytimes(lat, lon, current_date, method, 'standard')
                cache_prayer_times(lat, lon, date_str, method, 'standard', times)
            
            fasting_schedule.append({
                'day': day_num,
                'date': date_str,
                'suhoor_end': times['fajr'],
                'iftar_time': times['maghrib']
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
        
        # Calculate qibla direction
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        kaaba_lat_rad = math.radians(kaaba_lat)
        kaaba_lon_rad = math.radians(kaaba_lon)
        
        dlon = kaaba_lon_rad - lon_rad
        y = math.sin(dlon) * math.cos(kaaba_lat_rad)
        x = math.cos(lat_rad) * math.sin(kaaba_lat_rad) - \
            math.sin(lat_rad) * math.cos(kaaba_lat_rad) * math.cos(dlon)
        
        qibla = math.degrees(math.atan2(y, x))
        qibla = (qibla + 360) % 360
        
        return jsonify({
            'success': True,
            'qibla_direction': round(qibla, 2)
        })
        
    except Exception as e:
        print(f"❌ Qibla error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= MOSQUES ROUTE =============

@app.route('/api/mosques', methods=['POST'])
def get_mosques():
    """Get nearby mosques"""
    data = request.json
    
    try:
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        radius = float(data.get('radius', 10.0))
        
        query = """
            SELECT id, name, address, city, state, country,
                   latitude, longitude, phone,
                   ( 6371 * acos( cos( radians(%s) ) * cos( radians( latitude ) )
                   * cos( radians( longitude ) - radians(%s) )
                   + sin( radians(%s) ) * sin( radians( latitude ) ) ) ) AS distance
            FROM mosques
            WHERE verified = TRUE
            HAVING distance < %s
            ORDER BY distance
            LIMIT 50
        """
        
        mosques = execute_query(query, (lat, lon, lat, radius))
        
        return jsonify({
            'success': True,
            'mosques': mosques if mosques else []
        })
        
    except Exception as e:
        print(f"❌ Mosques error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

# ============= HEALTH CHECK =============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0',
        'praytimes_available': PRAYTIMES_AVAILABLE
    })

# ============= CALCULATION METHODS =============

@app.route('/api/calculation-methods', methods=['GET'])
def get_calculation_methods():
    """Get available calculation methods"""
    return jsonify({
        'success': True,
        'methods': list(CALCULATION_METHODS.keys())
    })

if __name__ == '__main__':
    print('🚀 Starting Worldwide Salah API...')
    print(f'📍 Prayer time calculation: {"ENABLED (praytimes library)" if PRAYTIMES_AVAILABLE else "DISABLED - install praytimes"}')
    print('🕌 Mosque queries: ENABLED')
    print('💾 PostgreSQL caching: ENABLED')
    app.run(host='0.0.0.0', port=5000, debug=True)