#!/usr/bin/env python3
"""
Worldwide Mosque Population Script
Populates mosques from major cities across the globe
"""

import requests
import time
from utils.db import execute_query

# ============= CONFIGURATION =============

# YOUR GOOGLE PLACES API KEY HERE
GOOGLE_API_KEY = "AIzaSyDeCo_hCRMWzr8FDuBoY-7cVVxvYF8n4Ws"

# ============= WORLDWIDE LOCATIONS =============
# Covering major cities across all continents with Muslim populations

SEARCH_LOCATIONS = [
    # ========== NORTH AMERICA ==========
    
    # United States - East Coast
    {'name': 'New York City, NY', 'lat': 40.7128, 'lng': -74.0060, 'radius': 25000},
    {'name': 'Brooklyn, NY', 'lat': 40.6782, 'lng': -73.9442, 'radius': 20000},
    {'name': 'Queens, NY', 'lat': 40.7282, 'lng': -73.7949, 'radius': 20000},
    {'name': 'Jersey City, NJ', 'lat': 40.7178, 'lng': -74.0431, 'radius': 15000},
    {'name': 'Philadelphia, PA', 'lat': 39.9526, 'lng': -75.1652, 'radius': 20000},
    {'name': 'Boston, MA', 'lat': 42.3601, 'lng': -71.0589, 'radius': 20000},
    {'name': 'Washington, DC', 'lat': 38.9072, 'lng': -77.0369, 'radius': 20000},
    {'name': 'Baltimore, MD', 'lat': 39.2904, 'lng': -76.6122, 'radius': 15000},
    {'name': 'Atlanta, GA', 'lat': 33.7490, 'lng': -84.3880, 'radius': 20000},
    {'name': 'Miami, FL', 'lat': 25.7617, 'lng': -80.1918, 'radius': 20000},
    
    # United States - Central
    {'name': 'Chicago, IL', 'lat': 41.8781, 'lng': -87.6298, 'radius': 25000},
    {'name': 'Detroit, MI', 'lat': 42.3314, 'lng': -83.0458, 'radius': 20000},
    {'name': 'Dearborn, MI', 'lat': 42.3223, 'lng': -83.1763, 'radius': 15000},
    {'name': 'Minneapolis, MN', 'lat': 44.9778, 'lng': -93.2650, 'radius': 15000},
    {'name': 'Dallas, TX', 'lat': 32.7767, 'lng': -96.7970, 'radius': 20000},
    {'name': 'Houston, TX', 'lat': 29.7604, 'lng': -95.3698, 'radius': 25000},
    
    # United States - West Coast
    {'name': 'Los Angeles, CA', 'lat': 34.0522, 'lng': -118.2437, 'radius': 30000},
    {'name': 'San Francisco, CA', 'lat': 37.7749, 'lng': -122.4194, 'radius': 20000},
    {'name': 'San Diego, CA', 'lat': 32.7157, 'lng': -117.1611, 'radius': 20000},
    {'name': 'Seattle, WA', 'lat': 47.6062, 'lng': -122.3321, 'radius': 15000},
    
    # Canada
    {'name': 'Toronto, Canada', 'lat': 43.6532, 'lng': -79.3832, 'radius': 25000},
    {'name': 'Mississauga, Canada', 'lat': 43.5890, 'lng': -79.6441, 'radius': 15000},
    {'name': 'Montreal, Canada', 'lat': 45.5017, 'lng': -73.5673, 'radius': 20000},
    {'name': 'Ottawa, Canada', 'lat': 45.4215, 'lng': -75.6972, 'radius': 15000},
    {'name': 'Vancouver, Canada', 'lat': 49.2827, 'lng': -123.1207, 'radius': 15000},
    
    # ========== EUROPE ==========
    
    # United Kingdom
    {'name': 'London, UK', 'lat': 51.5074, 'lng': -0.1278, 'radius': 30000},
    {'name': 'Birmingham, UK', 'lat': 52.4862, 'lng': -1.8904, 'radius': 20000},
    {'name': 'Manchester, UK', 'lat': 53.4808, 'lng': -2.2426, 'radius': 20000},
    {'name': 'Bradford, UK', 'lat': 53.7960, 'lng': -1.7594, 'radius': 15000},
    {'name': 'Leeds, UK', 'lat': 53.8008, 'lng': -1.5491, 'radius': 15000},
    
    # France
    {'name': 'Paris, France', 'lat': 48.8566, 'lng': 2.3522, 'radius': 25000},
    {'name': 'Marseille, France', 'lat': 43.2965, 'lng': 5.3698, 'radius': 20000},
    {'name': 'Lyon, France', 'lat': 45.7640, 'lng': 4.8357, 'radius': 15000},
    
    # Germany
    {'name': 'Berlin, Germany', 'lat': 52.5200, 'lng': 13.4050, 'radius': 25000},
    {'name': 'Frankfurt, Germany', 'lat': 50.1109, 'lng': 8.6821, 'radius': 15000},
    {'name': 'Munich, Germany', 'lat': 48.1351, 'lng': 11.5820, 'radius': 15000},
    
    # Netherlands
    {'name': 'Amsterdam, Netherlands', 'lat': 52.3676, 'lng': 4.9041, 'radius': 15000},
    {'name': 'Rotterdam, Netherlands', 'lat': 51.9225, 'lng': 4.4792, 'radius': 15000},
    
    # Belgium
    {'name': 'Brussels, Belgium', 'lat': 50.8503, 'lng': 4.3517, 'radius': 15000},
    
    # Spain
    {'name': 'Madrid, Spain', 'lat': 40.4168, 'lng': -3.7038, 'radius': 20000},
    {'name': 'Barcelona, Spain', 'lat': 41.3851, 'lng': 2.1734, 'radius': 20000},
    
    # Italy
    {'name': 'Rome, Italy', 'lat': 41.9028, 'lng': 12.4964, 'radius': 20000},
    {'name': 'Milan, Italy', 'lat': 45.4642, 'lng': 9.1900, 'radius': 15000},
    
    # Sweden
    {'name': 'Stockholm, Sweden', 'lat': 59.3293, 'lng': 18.0686, 'radius': 15000},
    
    # ========== MIDDLE EAST ==========
    
    # Saudi Arabia
    {'name': 'Mecca, Saudi Arabia', 'lat': 21.4225, 'lng': 39.8262, 'radius': 20000},
    {'name': 'Medina, Saudi Arabia', 'lat': 24.5247, 'lng': 39.5692, 'radius': 20000},
    {'name': 'Riyadh, Saudi Arabia', 'lat': 24.7136, 'lng': 46.6753, 'radius': 30000},
    {'name': 'Jeddah, Saudi Arabia', 'lat': 21.2854, 'lng': 39.2376, 'radius': 25000},
    {'name': 'Dammam, Saudi Arabia', 'lat': 26.4207, 'lng': 50.0888, 'radius': 20000},
    
    # United Arab Emirates
    {'name': 'Dubai, UAE', 'lat': 25.2048, 'lng': 55.2708, 'radius': 30000},
    {'name': 'Abu Dhabi, UAE', 'lat': 24.4539, 'lng': 54.3773, 'radius': 25000},
    {'name': 'Sharjah, UAE', 'lat': 25.3463, 'lng': 55.4209, 'radius': 20000},
    
    # Qatar
    {'name': 'Doha, Qatar', 'lat': 25.2854, 'lng': 51.5310, 'radius': 20000},
    
    # Kuwait
    {'name': 'Kuwait City, Kuwait', 'lat': 29.3759, 'lng': 47.9774, 'radius': 20000},
    
    # Bahrain
    {'name': 'Manama, Bahrain', 'lat': 26.0667, 'lng': 50.5577, 'radius': 15000},
    
    # Oman
    {'name': 'Muscat, Oman', 'lat': 23.5880, 'lng': 58.3829, 'radius': 20000},
    
    # Jordan
    {'name': 'Amman, Jordan', 'lat': 31.9454, 'lng': 35.9284, 'radius': 20000},
    
    # Lebanon
    {'name': 'Beirut, Lebanon', 'lat': 33.8938, 'lng': 35.5018, 'radius': 15000},
    
    # Turkey
    {'name': 'Istanbul, Turkey', 'lat': 41.0082, 'lng': 28.9784, 'radius': 30000},
    {'name': 'Ankara, Turkey', 'lat': 39.9334, 'lng': 32.8597, 'radius': 20000},
    {'name': 'Izmir, Turkey', 'lat': 38.4237, 'lng': 27.1428, 'radius': 20000},
    
    # Iran
    {'name': 'Tehran, Iran', 'lat': 35.6892, 'lng': 51.3890, 'radius': 30000},
    {'name': 'Mashhad, Iran', 'lat': 36.2605, 'lng': 59.6168, 'radius': 20000},
    {'name': 'Isfahan, Iran', 'lat': 32.6546, 'lng': 51.6680, 'radius': 20000},
    
    # Iraq
    {'name': 'Baghdad, Iraq', 'lat': 33.3152, 'lng': 44.3661, 'radius': 25000},
    
    # ========== SOUTH ASIA ==========
    
    # Pakistan
    {'name': 'Karachi, Pakistan', 'lat': 24.8607, 'lng': 67.0011, 'radius': 30000},
    {'name': 'Lahore, Pakistan', 'lat': 31.5204, 'lng': 74.3587, 'radius': 25000},
    {'name': 'Islamabad, Pakistan', 'lat': 33.6844, 'lng': 73.0479, 'radius': 20000},
    {'name': 'Rawalpindi, Pakistan', 'lat': 33.5651, 'lng': 73.0169, 'radius': 15000},
    {'name': 'Faisalabad, Pakistan', 'lat': 31.4504, 'lng': 73.1350, 'radius': 20000},
    
    # India
    {'name': 'Delhi, India', 'lat': 28.7041, 'lng': 77.1025, 'radius': 30000},
    {'name': 'Mumbai, India', 'lat': 19.0760, 'lng': 72.8777, 'radius': 30000},
    {'name': 'Hyderabad, India', 'lat': 17.3850, 'lng': 78.4867, 'radius': 25000},
    {'name': 'Bangalore, India', 'lat': 12.9716, 'lng': 77.5946, 'radius': 25000},
    {'name': 'Lucknow, India', 'lat': 26.8467, 'lng': 80.9462, 'radius': 20000},
    
    # Bangladesh
    {'name': 'Dhaka, Bangladesh', 'lat': 23.8103, 'lng': 90.4125, 'radius': 25000},
    {'name': 'Chittagong, Bangladesh', 'lat': 22.3569, 'lng': 91.7832, 'radius': 20000},
    
    # Afghanistan
    {'name': 'Kabul, Afghanistan', 'lat': 34.5553, 'lng': 69.2075, 'radius': 20000},
    
    # ========== SOUTHEAST ASIA ==========
    
    # Indonesia
    {'name': 'Jakarta, Indonesia', 'lat': -6.2088, 'lng': 106.8456, 'radius': 30000},
    {'name': 'Surabaya, Indonesia', 'lat': -7.2575, 'lng': 112.7521, 'radius': 25000},
    {'name': 'Bandung, Indonesia', 'lat': -6.9175, 'lng': 107.6191, 'radius': 20000},
    {'name': 'Medan, Indonesia', 'lat': 3.5952, 'lng': 98.6722, 'radius': 20000},
    
    # Malaysia
    {'name': 'Kuala Lumpur, Malaysia', 'lat': 3.1390, 'lng': 101.6869, 'radius': 25000},
    {'name': 'Penang, Malaysia', 'lat': 5.4164, 'lng': 100.3327, 'radius': 15000},
    {'name': 'Johor Bahru, Malaysia', 'lat': 1.4927, 'lng': 103.7414, 'radius': 15000},
    
    # Singapore
    {'name': 'Singapore', 'lat': 1.3521, 'lng': 103.8198, 'radius': 20000},
    
    # Brunei
    {'name': 'Bandar Seri Begawan, Brunei', 'lat': 4.9031, 'lng': 114.9398, 'radius': 10000},
    
    # Thailand
    {'name': 'Bangkok, Thailand', 'lat': 13.7563, 'lng': 100.5018, 'radius': 20000},
    
    # ========== AFRICA ==========
    
    # Egypt
    {'name': 'Cairo, Egypt', 'lat': 30.0444, 'lng': 31.2357, 'radius': 30000},
    {'name': 'Alexandria, Egypt', 'lat': 31.2001, 'lng': 29.9187, 'radius': 20000},
    
    # Morocco
    {'name': 'Casablanca, Morocco', 'lat': 33.5731, 'lng': -7.5898, 'radius': 20000},
    {'name': 'Rabat, Morocco', 'lat': 34.0209, 'lng': -6.8416, 'radius': 15000},
    {'name': 'Marrakech, Morocco', 'lat': 31.6295, 'lng': -7.9811, 'radius': 15000},
    
    # Algeria
    {'name': 'Algiers, Algeria', 'lat': 36.7538, 'lng': 3.0588, 'radius': 20000},
    
    # Tunisia
    {'name': 'Tunis, Tunisia', 'lat': 36.8065, 'lng': 10.1815, 'radius': 15000},
    
    # Libya
    {'name': 'Tripoli, Libya', 'lat': 32.8872, 'lng': 13.1913, 'radius': 20000},
    
    # Sudan
    {'name': 'Khartoum, Sudan', 'lat': 15.5007, 'lng': 32.5599, 'radius': 20000},
    
    # Nigeria
    {'name': 'Lagos, Nigeria', 'lat': 6.5244, 'lng': 3.3792, 'radius': 25000},
    {'name': 'Kano, Nigeria', 'lat': 12.0022, 'lng': 8.5920, 'radius': 20000},
    
    # Senegal
    {'name': 'Dakar, Senegal', 'lat': 14.7167, 'lng': -17.4677, 'radius': 15000},
    
    # South Africa
    {'name': 'Johannesburg, South Africa', 'lat': -26.2041, 'lng': 28.0473, 'radius': 20000},
    {'name': 'Cape Town, South Africa', 'lat': -33.9249, 'lng': 18.4241, 'radius': 20000},
    {'name': 'Durban, South Africa', 'lat': -29.8587, 'lng': 31.0218, 'radius': 15000},
    
    # Somalia
    {'name': 'Mogadishu, Somalia', 'lat': 2.0469, 'lng': 45.3182, 'radius': 15000},
    
    # Kenya
    {'name': 'Nairobi, Kenya', 'lat': -1.2921, 'lng': 36.8219, 'radius': 20000},
    
    # ========== CENTRAL ASIA ==========
    
    # Kazakhstan
    {'name': 'Almaty, Kazakhstan', 'lat': 43.2220, 'lng': 76.8512, 'radius': 20000},
    
    # Uzbekistan
    {'name': 'Tashkent, Uzbekistan', 'lat': 41.2995, 'lng': 69.2401, 'radius': 20000},
    
    # ========== EAST ASIA ==========
    
    # China
    {'name': 'Beijing, China', 'lat': 39.9042, 'lng': 116.4074, 'radius': 25000},
    {'name': 'Shanghai, China', 'lat': 31.2304, 'lng': 121.4737, 'radius': 25000},
    
    # ========== AUSTRALIA & OCEANIA ==========
    
    # Australia
    {'name': 'Sydney, Australia', 'lat': -33.8688, 'lng': 151.2093, 'radius': 25000},
    {'name': 'Melbourne, Australia', 'lat': -37.8136, 'lng': 144.9631, 'radius': 25000},
    {'name': 'Perth, Australia', 'lat': -31.9505, 'lng': 115.8605, 'radius': 20000},
    {'name': 'Brisbane, Australia', 'lat': -27.4698, 'lng': 153.0251, 'radius': 20000},
]

# ============= FUNCTIONS (Same as before) =============

def search_mosques(lat, lng, radius, api_key):
    """Search for mosques using Google Places API"""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    params = {
        'location': f'{lat},{lng}',
        'radius': radius,
        'keyword': 'mosque masjid',
        'key': api_key,
    }
    
    print(f"  🔍 Searching...")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['status'] == 'OK':
                results = data.get('results', [])
                print(f"  ✅ Found {len(results)} mosques")
                return results
            elif data['status'] == 'ZERO_RESULTS':
                print("  ⚠️ No mosques found")
                return []
            else:
                print(f"  ❌ API Error: {data['status']}")
                return []
        else:
            print(f"  ❌ HTTP Error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []

def get_place_details(place_id, api_key):
    """Get detailed information about a place"""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    
    params = {
        'place_id': place_id,
        'fields': 'formatted_phone_number,website,formatted_address',
        'key': api_key,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['status'] == 'OK':
                result = data.get('result', {})
                return {
                    'phone': result.get('formatted_phone_number'),
                    'website': result.get('website'),
                    'address': result.get('formatted_address'),
                }
        
        return {'phone': None, 'website': None, 'address': None}
        
    except Exception as e:
        return {'phone': None, 'website': None, 'address': None}

def extract_city_country(address):
    """Extract city and country from formatted address"""
    if not address:
        return 'Unknown', 'Unknown'
    
    parts = [p.strip() for p in address.split(',')]
    
    if len(parts) >= 2:
        country = parts[-1]  # Country is always last
        city = parts[-2] if len(parts) >= 2 else 'Unknown'
        return city, country
    
    return 'Unknown', 'Unknown'

def insert_mosque(mosque_data):
    """Insert mosque into database"""
    try:
        query = """
            INSERT INTO mosques 
            (name, address, city, country, latitude, longitude, phone, website, verified)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT DO NOTHING
            RETURNING mosque_id
        """
        
        result = execute_query(query, (
            mosque_data['name'],
            mosque_data['address'],
            mosque_data['city'],
            mosque_data['country'],
            mosque_data['latitude'],
            mosque_data['longitude'],
            mosque_data['phone'],
            mosque_data['website'],
        ), fetch_one=True)
        
        if result:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False

def process_location(location_config, api_key):
    """Process one location - search and insert mosques"""
    print(f"\n📍 {location_config['name']}")
    
    # Search for mosques
    places = search_mosques(
        location_config['lat'],
        location_config['lng'],
        location_config['radius'],
        api_key
    )
    
    if not places:
        return 0
    
    inserted_count = 0
    
    for i, place in enumerate(places, 1):
        # Get detailed information
        details = get_place_details(place['place_id'], api_key)
        
        # Extract data
        location = place['geometry']['location']
        address = details['address'] or place.get('vicinity', '')
        city, country = extract_city_country(address)
        
        mosque_data = {
            'name': place['name'],
            'address': address,
            'city': city,
            'country': country,
            'latitude': location['lat'],
            'longitude': location['lng'],
            'phone': details['phone'],
            'website': details['website'],
        }
        
        # Insert into database
        if insert_mosque(mosque_data):
            inserted_count += 1
            print(f"    ✓ {i}/{len(places)}: {place['name'][:50]}")
        
        # Rate limiting - Google allows 10 requests/second
        time.sleep(0.15)  # 150ms delay
    
    print(f"  → Inserted: {inserted_count}/{len(places)}")
    return inserted_count

# ============= MAIN SCRIPT =============

def main():
    """Main function - populate mosques worldwide"""
    print("🌍 WORLDWIDE SALAH - Global Mosque Population")
    print("=" * 70)
    
    # Check API key
    if GOOGLE_API_KEY == "YOUR_API_KEY_HERE":
        print("❌ ERROR: Please set your Google API key!")
        print("   Edit the script and replace YOUR_API_KEY_HERE on line 13")
        return
    
    print(f"📋 Configured {len(SEARCH_LOCATIONS)} cities worldwide")
    print(f"🔑 API Key: {GOOGLE_API_KEY[:10]}...")
    print(f"⏱️  Estimated time: {len(SEARCH_LOCATIONS) * 2} minutes")
    print("=" * 70)
    
    # Process each location
    total_inserted = 0
    start_time = time.time()
    
    for i, location in enumerate(SEARCH_LOCATIONS, 1):
        print(f"\n[{i}/{len(SEARCH_LOCATIONS)}]", end=" ")
        inserted = process_location(location, GOOGLE_API_KEY)
        total_inserted += inserted
        
        # Progress update every 10 cities
        if i % 10 == 0:
            elapsed = time.time() - start_time
            print(f"\n  ⏱️  Progress: {i}/{len(SEARCH_LOCATIONS)} cities, "
                  f"{total_inserted} mosques, {elapsed/60:.1f} minutes elapsed")
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"✅ COMPLETE!")
    print(f"   🕌 Total mosques inserted: {total_inserted}")
    print(f"   🌍 Cities processed: {len(SEARCH_LOCATIONS)}")
    print(f"   ⏱️  Time taken: {elapsed/60:.1f} minutes")
    print("=" * 70)
    print("\n🎉 Your database now has mosques from around the world!")
    print("   Test in your app: flutter run")

if __name__ == '__main__':
    main()