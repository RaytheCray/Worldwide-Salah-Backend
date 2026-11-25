# utils/mosque_finder.py - Nearby mosque search backed by OpenStreetMap
#
# The mosques table starts almost empty, so when an area hasn't been searched
# recently we ask OpenStreetMap's Overpass API for mosques around it and store
# them. Later requests for the same area are served from the database.
import os
import requests
from utils.db import get_connection, execute_query

OVERPASS_URL = os.getenv('OVERPASS_URL', 'https://overpass-api.de/api/interpreter')
# Overpass usage policy asks clients to identify themselves
USER_AGENT = 'WorldwideSalah/1.0 (+https://github.com/RaytheCray/Worldwide-Salah-Backend)'
SEARCH_REFRESH_DAYS = 30

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

def _fetch_from_overpass(lat, lon, radius_km):
    """Return mosques around a point as dicts ready for the mosques table"""
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
            'osm_ref': f"{element['type']}/{element['id']}",
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
                (osm_ref, name, address, city, country, latitude, longitude, phone, website, verified)
                VALUES (%(osm_ref)s, %(name)s, %(address)s, %(city)s, %(country)s,
                        %(latitude)s, %(longitude)s, %(phone)s, %(website)s, TRUE)
                ON CONFLICT (osm_ref) DO UPDATE SET
                    name = EXCLUDED.name,
                    address = EXCLUDED.address,
                    city = EXCLUDED.city,
                    country = EXCLUDED.country,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    phone = EXCLUDED.phone,
                    website = EXCLUDED.website
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
    """Fetch mosques from OpenStreetMap unless this area was searched recently"""
    lat_key, lon_key = _area_key(lat, lon)
    if _area_recently_searched(lat_key, lon_key, radius_km):
        return

    try:
        # Search slightly wider than requested to cover the rounding of the area key
        mosques = _fetch_from_overpass(lat_key, lon_key, radius_km + 2)
        _store_search(lat_key, lon_key, radius_km, mosques)
        print(f"🌍 OpenStreetMap: stored {len(mosques)} mosques near {lat_key}, {lon_key}")
    except Exception as e:
        # Serve whatever is already in the database; the next request will retry
        print(f"⚠️ OpenStreetMap lookup failed: {e}")

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
