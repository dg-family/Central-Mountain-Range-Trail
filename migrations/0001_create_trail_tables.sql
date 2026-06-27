-- Migration: Create trail tables
-- Created: 2024-12-24
-- Description: Initial schema for 思源啞口登山步道 trail data

-- Trail metadata table
CREATE TABLE trail_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    osm_way_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    highway_type TEXT,
    total_nodes INTEGER,
    min_lat REAL,
    max_lat REAL,
    min_lon REAL,
    max_lon REAL,
    created_by TEXT,
    changeset_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Trail coordinates table
CREATE TABLE trail_coordinates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trail_id INTEGER,
    osm_node_id INTEGER NOT NULL,
    sequence_order INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    name TEXT,
    description TEXT,
    is_waypoint BOOLEAN DEFAULT FALSE,
    tags TEXT, -- JSON string for additional tags
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trail_id) REFERENCES trail_metadata(id)
);

-- Create indexes for better query performance
CREATE INDEX idx_trail_coordinates_trail_id ON trail_coordinates(trail_id);
CREATE INDEX idx_trail_coordinates_osm_node_id ON trail_coordinates(osm_node_id);
CREATE INDEX idx_trail_coordinates_sequence ON trail_coordinates(trail_id, sequence_order);
CREATE INDEX idx_trail_coordinates_location ON trail_coordinates(latitude, longitude);