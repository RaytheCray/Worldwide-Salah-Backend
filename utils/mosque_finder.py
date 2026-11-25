# utils/mosque_finder.py - Nearby mosque search backed by Google Places and OpenStreetMap
#
# The mosques table starts almost empty, so when an area hasn't been searched
# recently we look up mosques around it and store them. Google Places is used
# when GOOGLE_API_KEY is set; OpenStreetMap's Overpass API is the fallback.
# Later requests for the same area are served from the database.
import os
import time
import requests
from utils.db import get_connection, execute_query

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_NEARBY_URL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
GOOGLE_MAX_PAGES = 3  # Nearby Search returns at most 20 results per page, 60 in total

OVERPASS_URL = os.getenv('OVERPASS_URL', 'https://overpass-api.de/api/interpreter')
# Overpass usage policy asks clients to identify themselves
USER_AGENT = 'WorldwideSalah/1.0 (+https://github.com/RaytheCray/Worldwide-Salah-Backend)'
SEARCH_REFRESH_DAYS = 30

def _redact(message):
    """Keep the API key out of logs (request errors include the full URL)"""
    message = str(message)
    return message.replace(GOOGLE_API_KEY, '***') if GOOGLE_API_KEY else message

def _area_key(lat, lon):
    """Round to ~1 km so nearby requests share one search"""
    return round(lat, 2), round(lon, 2)

def _area_recently_searched(lat_key, lon_key, radius_km):
    result = execute_query("""
        SELECT 1 FROM mosque_search_areas
        WHERE lat_key = %s AND lon_key = %s
          AND radius_km >= %s
          AND searched_at > NOW() - make_interval(days => %s)
    """, (lat_key, lon_key, radius_km, SEARCH_REFRESH_DAYS), fetch_one=True)
    return result is not None

def _fetch_from_google(lat, lon, radius_km):
    """Return mosques around a point from Google Places Nearby Search"""
    params = {
        'location': f'{lat},{lon}',
        'radius': min(int(radius_km * 1000), 50000),
        'type': 'mosque',
        'key': GOOGLE_API_KEY,
    }

    places = []
    for page in range(GOOGLE_MAX_PAGES):
        data = requests.get(GOOGLE_NEARBY_URL, params=params, timeout=15).json()
        status = data.get('status')

        # A next_page_token takes a moment to become valid
        if status == 'INVALID_REQUEST' and page > 0:
            time.sleep(2)
            data = requests.get(GOOGLE_NEARBY_URL, params=params, timeout=15).json()
            status = data.get('status')

        if status == 'ZERO_RESULTS':
            break
        if status != 'OK':
            raise Exception(f"Google Places error {status}: {data.get('error_message', '')}")

        places.extend(data.get('results', []))

        token = data.get('next_page_token')
        if not token:
            break
        params = {'pagetoken': token, 'key': GOOGLE_API_KEY}
        time.sleep(2)

    return [{
        'source_ref': f"google:{place['place_id']}",
        'name': place['name'],
        'address': place.get('vicinity'),
        'city': None,
        'country': None,
        'latitude': place['geometry']['location']['lat'],
        'longitude': place['geometry']['location']['lng'],
        'phone': None,
        'website': None,
    } for place in places]

def _fetch_from_overpass(lat, lon, radius_km):
    """Return mosques around a point from OpenStreetMap"""
    radius_m = int(radius_km * 1000)
    query = f"""
        [out:json][timeout:20];
        (
          node["amenity"="place_of_worship"]["religion"="muslim"](around:{radius_m},{lat},{lon});
          way["amenity"="place_of_worship"]["religion"="muslim"](around:{radius_m},{lat},{lon});
          relation["amenity"="place_of_worship"]["religion"="muslim"](around:{radius_m},{lat},{lon});
        );
        out center tags;
    """
    response = requests.post(
        OVERPASS_URL,
        data={'data': query},
        headers={'User-Agent': USER_AGENT},
        timeout=25,
    )
    response.raise_for_status()

    mosques = []
    for element in response.json().get('elements', []):
        # Nodes carry coordinates directly; ways and relations get a computed center
        point = element if element['type'] == 'node' else element.get('center')
        if not point:
            continue

        tags = element.get('tags', {})
        street = ' '.join(filter(None, [tags.get('addr:housenumber'), tags.get('addr:street')]))

        mosques.append({
            'source_ref': f"osm:{element['type']}/{element['id']}",
            'name': tags.get('name:en') or tags.get('name') or 'Mosque',
            'address': street or None,
            'city': tags.get('addr:city'),
            'country': tags.get('addr:country'),
            'latitude': point['lat'],
            'longitude': point['lon'],
            'phone': tags.get('phone') or tags.get('contact:phone'),
            'website': tags.get('website') or tags.get('contact:website'),
        })
    return mosques

def _store_search(lat_key, lon_key, radius_km, mosques):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO mosques
                (source_ref, name, address, city, country, latitude, longitude, phone, website, verified)
                VALUES (%(source_ref)s, %(name)s, %(address)s, %(city)s, %(country)s,
                        %(latitude)s, %(longitude)s, %(phone)s, %(website)s, TRUE)
                ON CONFLICT (source_ref) DO UPDATE SET
                    name = EXCLUDED.name,
                    address = COALESCE(EXCLUDED.address, mosques.address),
                    city = COALESCE(EXCLUDED.city, mosques.city),
                    country = COALESCE(EXCLUDED.country, mosques.country),
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    phone = COALESCE(EXCLUDED.phone, mosques.phone),
                    website = COALESCE(EXCLUDED.website, mosques.website)
            """, mosques)
            cur.execute("""
                INSERT INTO mosque_search_areas (lat_key, lon_key, radius_km, searched_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (lat_key, lon_key) DO UPDATE SET
                    radius_km = GREATEST(mosque_search_areas.radius_km, EXCLUDED.radius_km),
                    searched_at = NOW()
            """, (lat_key, lon_key, radius_km))
        conn.commit()

def refresh_area_if_needed(lat, lon, radius_km):
    """Look up mosques for this area unless it was searched recently"""
    lat_key, lon_key = _area_key(lat, lon)
    if _area_recently_searched(lat_key, lon_key, radius_km):
        return

    sources = [('OpenStreetMap', _fetch_from_overpass)]
    if GOOGLE_API_KEY:
        sources.insert(0, ('Google Places', _fetch_from_google))

    for source_name, fetch in sources:
        try:
            # Search slightly wider than requested to cover the rounding of the area key
            mosques = fetch(lat_key, lon_key, radius_km + 2)
            _store_search(lat_key, lon_key, radius_km, mosques)
            print(f"🌍 {source_name}: stored {len(mosques)} mosques near {lat_key}, {lon_key}")
            return
        except Exception as e:
            print(f"⚠️ {source_name} lookup failed: {_redact(e)}")

    # Every source failed: serve what the database has; the next request will retry

def find_nearby_mosques(lat, lon, radius_km):
    """Mosques within radius_km of a point, nearest first"""
    refresh_area_if_needed(lat, lon, radius_km)

    # LEAST/GREATEST keep acos() in its domain when a mosque is at the exact search point
    return execute_query("""
        SELECT * FROM (
            SELECT
                mosque_id, name, address, city, country,
                latitude, longitude, phone, website,
                6371 * acos(LEAST(1, GREATEST(-1,
                    cos(radians(%s)) * cos(radians(latitude)) *
                    cos(radians(longitude) - radians(%s)) +
                    sin(radians(%s)) * sin(radians(latitude))
                ))) AS distance
            FROM mosques
            WHERE verified = TRUE
        ) nearby
        WHERE distance < %s
        ORDER BY distance
        LIMIT 50
    """, (lat, lon, lat, radius_km)) or []
