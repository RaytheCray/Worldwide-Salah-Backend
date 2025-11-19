-- Worldwide Salah Database Schema
-- PostgreSQL Database Setup

-- Create database (run this separately as postgres user)
-- CREATE DATABASE worldwide_salah;

-- Users table - store user information and preferences
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences table - store calculation methods and settings
CREATE TABLE user_preferences (
    preference_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    calculation_method VARCHAR(50) DEFAULT 'ISNA', -- ISNA, MWL, EGYPTIAN, etc.
    asr_method VARCHAR(20) DEFAULT 'standard', -- standard or hanafi
    theme VARCHAR(20) DEFAULT 'light', -- light or dark
    language VARCHAR(10) DEFAULT 'en',
    notifications_enabled BOOLEAN DEFAULT true,
    adhan_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- User locations table - store saved locations for users
CREATE TABLE user_locations (
    location_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    location_name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    city VARCHAR(255),
    country VARCHAR(255),
    timezone VARCHAR(100),
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Mosques table - store mosque information
CREATE TABLE mosques (
    mosque_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(255),
    country VARCHAR(255),
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    phone VARCHAR(50),
    website VARCHAR(255),
    verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Mosque prayer times table - store congregational prayer times
CREATE TABLE mosque_prayer_times (
    prayer_time_id SERIAL PRIMARY KEY,
    mosque_id INTEGER REFERENCES mosques(mosque_id) ON DELETE CASCADE,
    prayer_name VARCHAR(20) NOT NULL, -- Fajr, Dhuhr, Asr, Maghrib, Isha
    prayer_time TIME NOT NULL,
    day_of_week INTEGER, -- 0-6 (Sunday to Saturday), NULL for all days
    effective_date DATE, -- When this time becomes effective
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prayer time cache table - cache calculated prayer times
CREATE TABLE prayer_time_cache (
    cache_id SERIAL PRIMARY KEY,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    calculation_method VARCHAR(50) NOT NULL,
    asr_method VARCHAR(20) NOT NULL,
    prayer_date DATE NOT NULL,
    fajr_time TIME NOT NULL,
    sunrise_time TIME NOT NULL,
    dhuhr_time TIME NOT NULL,
    asr_time TIME NOT NULL,
    maghrib_time TIME NOT NULL,
    isha_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(latitude, longitude, calculation_method, asr_method, prayer_date)
);

-- Ramadan dates table - store Ramadan start/end dates
CREATE TABLE ramadan_dates (
    ramadan_id SERIAL PRIMARY KEY,
    hijri_year INTEGER NOT NULL UNIQUE,
    gregorian_year INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notification logs table - track sent notifications
CREATE TABLE notification_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    notification_type VARCHAR(50), -- prayer_time, ramadan_reminder, etc.
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    prayer_name VARCHAR(20),
    status VARCHAR(20) DEFAULT 'sent' -- sent, failed, pending
);

-- Create indexes for better query performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_user_locations_user_id ON user_locations(user_id);
CREATE INDEX idx_user_locations_coords ON user_locations(latitude, longitude);
CREATE INDEX idx_mosques_coords ON mosques(latitude, longitude);
CREATE INDEX idx_mosques_city_country ON mosques(city, country);
CREATE INDEX idx_mosque_prayer_times_mosque_id ON mosque_prayer_times(mosque_id);
CREATE INDEX idx_prayer_time_cache_coords ON prayer_time_cache(latitude, longitude, prayer_date);
CREATE INDEX idx_ramadan_dates_year ON ramadan_dates(gregorian_year);
CREATE INDEX idx_notification_logs_user_id ON notification_logs(user_id, sent_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_locations_updated_at BEFORE UPDATE ON user_locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mosques_updated_at BEFORE UPDATE ON mosques
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mosque_prayer_times_updated_at BEFORE UPDATE ON mosque_prayer_times
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample Ramadan dates
INSERT INTO ramadan_dates (hijri_year, gregorian_year, start_date, end_date) VALUES
(1446, 2025, '2025-02-28', '2025-03-30'),
(1447, 2026, '2026-02-17', '2026-03-19'),
(1448, 2027, '2027-02-06', '2027-03-08');

-- Sample mosque data (New York area)
INSERT INTO mosques (name, address, city, country, latitude, longitude, phone, verified) VALUES
('Islamic Cultural Center of New York', '1711 3rd Ave', 'New York', 'USA', 40.7812, -73.9537, '212-722-5234', true),
('Masjid Malcolm Shabazz', '102 W 116th St', 'New York', 'USA', 40.8007, -73.9476, '212-662-2200', true),
('Islamic Center at NYU', '238 Thompson St', 'New York', 'USA', 40.7290, -73.9968, '212-998-4300', true);

-- Sample congregational prayer times for one mosque
INSERT INTO mosque_prayer_times (mosque_id, prayer_name, prayer_time) VALUES
(1, 'Fajr', '05:45:00'),
(1, 'Dhuhr', '13:15:00'),
(1, 'Asr', '15:15:00'),
(1, 'Maghrib', '14:35:00'),
(1, 'Isha', '20:00:00');