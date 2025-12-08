# Using IslamicFinder API-compatible calculations

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from utils.db import execute_query
import math
import requests

app = Flask(__name__)
CORS(app)

def calculate_prayer_times_accurate(lat, lon, date, method='ISNA', asr_method='standard'):
    """
    Calculate prayer times using the Aladhan API (free, reliable, accurate)
    This is what IslamicFinder and most apps use behind the scenes
    """
    try:
        # Format date
        date_str = date.strftime('%d-%m-%Y')
        
        # Method mapping to Aladhan API codes
        method_codes = {
            'ISNA': 2,
            'MWL': 3,
            'EGYPTIAN': 5,
            'KARACHI': 1,
            'MAKKAH': 4,
            'TEHRAN': 7
        }
        
        method_code = method_codes.get(method, 2)
        
        # School mapping (0 = Standard Shafi, 1 = Hanafi)
        school = 1 if asr_method == 'hanafi' else 0
        
        # Call Aladhan API
        url = f'http://api.aladhan.com/v1/timings/{date_str}'
        params = {
            'latitude': lat,
            'longitude': lon,
            'method': method_code,
            'school': school
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['code'] == 200:
                timings = data['data']['timings']
                
                # Extract and format times (they come as HH:MM)
                times = {
                    'fajr': timings['Fajr'],
                    'sunrise': timings['Sunrise'],
                    'dhuhr': timings['Dhuhr'],
                    'asr': timings['Asr'],
                    'maghrib': timings['Maghrib'],
                    'isha': timings['Isha']
                }
                
                print(f"✅ Prayer times calculated via Aladhan API:")
                print(f"   Location: {lat:.4f}, {lon:.4f}")
                print(f"   Date: {date.strftime('%Y-%m-%d')}")
                print(f"   Method: {method}, Asr: {asr_method}")
                print(f"   Fajr: {times['fajr']}, Sunrise: {times['sunrise']}, Dhuhr: {times['dhuhr']}")
                print(f"   Asr: {times['asr']}, Maghrib: {times['maghrib']}, Isha: {times['isha']}")
                
                return times
            else:
                raise Exception(f"Aladhan API error: {data.get('data', 'Unknown error')}")
        else:
            raise Exception(f"HTTP error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Prayer time calculation error: {e}")
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
        
        # Calculate new times using Aladhan API
        print(f"🔄 Calculating prayer times via Aladhan API for {date_str}")
        times = calculate_prayer_times_accurate(lat, lon, date, method, asr_method)
        
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
                times = calculate_prayer_times_accurate(lat, lon, date, method, asr_method)
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
                times = calculate_prayer_times_accurate(lat, lon, current_date, method, 'standard')
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
    
@app.route('/api/mosques/nearby', methods=['GET'])
def get_mosques_nearby_get():
    """Get nearby mosques (GET method for compatibility)"""
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        radius = float(request.args.get('radius', 10.0))
        
        query = """
            SELECT mosque_id, name, address, city, state, country,
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
        
        mosques = execute_query(query, (lat, lng, lat, radius))
        
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
        'calculation_method': 'Aladhan API'
    })

# ============= CALCULATION METHODS =============

@app.route('/api/calculation-methods', methods=['GET'])
def get_calculation_methods():
    """Get available calculation methods"""
    return jsonify({
        'success': True,
        'methods': ['ISNA', 'MWL', 'EGYPTIAN', 'KARACHI', 'MAKKAH', 'TEHRAN']
    })

if __name__ == '__main__':
    print('🚀 Starting Worldwide Salah API...')
    print('📍 Prayer time calculation: ENABLED (Aladhan API)')
    print('🕌 Mosque queries: ENABLED')
    print('💾 PostgreSQL caching: ENABLED')
    app.run(host='0.0.0.0', port=5000, debug=True)