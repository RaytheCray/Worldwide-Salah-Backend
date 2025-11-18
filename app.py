from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import math
from hijri_converter import Hijri, Gregorian

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter app

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
        times = calculate_prayer_times(lat, lon, date, method, asr_method)
        
        return jsonify({
            'success': True,
            'date': date_str,
            'times': times,
            'method': method,
            'asr_method': asr_method
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
            times = calculate_prayer_times(lat, lon, date, method, asr_method)
            monthly_times.append({
                'date': date.strftime('%Y-%m-%d'),
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

@app.route('/api/ramadan', methods=['POST'])
def get_ramadan_info():
    """Get Ramadan start/end dates and fasting times"""
    data = request.json
    
    try:
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        year = int(data.get('year', datetime.now().year))
        method = data.get('method', 'ISNA')
        
        # Calculate Ramadan dates (Ramadan is 9th month of Hijri calendar)
        hijri_start = Hijri(year - 621, 9, 1)  # Approximate conversion
        greg_start = hijri_start.to_gregorian()
        
        # Ramadan is 29-30 days
        ramadan_days = []
        for day in range(30):
            date = datetime(greg_start.year, greg_start.month, greg_start.day) + timedelta(days=day)
            times = calculate_prayer_times(lat, lon, date, method)
            
            ramadan_days.append({
                'date': date.strftime('%Y-%m-%d'),
                'day': day + 1,
                'suhoor_end': times['fajr'],  # Stop eating at Fajr
                'iftar': times['maghrib']  # Break fast at Maghrib
            })
        
        return jsonify({
            'success': True,
            'year': year,
            'start_date': ramadan_days[0]['date'],
            'end_date': ramadan_days[-1]['date'],
            'fasting_schedule': ramadan_days
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

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
    return jsonify({
        'success': True,
        'status': 'running',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)