-- PostgreSQL / Supabase: existing data is preserved.
CREATE TABLE IF NOT EXISTS traffic_information (
        traffic_id SERIAL PRIMARY KEY,
        road_name VARCHAR(100),
        road_type VARCHAR(50),
        link_id VARCHAR(100),
        speed NUMERIC,
        travel_time NUMERIC,
        traffic_status VARCHAR(20),
        latitude DECIMAL(10, 7),
        longitude DECIMAL(10, 7),
        collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
