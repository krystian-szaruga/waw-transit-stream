CREATE TABLE IF NOT EXISTS gtfs_versions (
     version_id BIGSERIAL PRIMARY KEY,
     sha256 CHAR(64) NOT NULL UNIQUE,
     loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
     status TEXT NOT NULL DEFAULT 'loading'
         CHECK (status IN ('loading', 'active', 'retired'))
);

CREATE TABLE IF NOT EXISTS gtfs_feed_state (
     id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
     etag TEXT,
     last_modified TEXT
);

INSERT INTO gtfs_feed_state (id) VALUES (1) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS static_timetable (
     gtfs_version BIGINT NOT NULL REFERENCES gtfs_versions(version_id),
     service_date DATE NOT NULL,
     vehicle_type SMALLINT NOT NULL,
     line VARCHAR(10) NOT NULL,
     brigade VARCHAR(10) NOT NULL,
     route_id VARCHAR(50) NOT NULL,
     trip_id VARCHAR(50) NOT NULL,
     stop_id VARCHAR(50) NOT NULL,
     stop_name VARCHAR(255),
     stop_sequence INT NOT NULL,
     stop_lat DOUBLE PRECISION NOT NULL,
     stop_lon DOUBLE PRECISION NOT NULL,
     scheduled_arrival_offset INT NOT NULL,
     PRIMARY KEY (gtfs_version, service_date, trip_id, stop_sequence)
 );

CREATE TABLE IF NOT EXISTS gtfs_trip_shapes (
     gtfs_version BIGINT NOT NULL REFERENCES gtfs_versions(version_id),
     trip_id VARCHAR(50) NOT NULL,
     shape_id VARCHAR(50) NOT NULL,
     PRIMARY KEY (gtfs_version, trip_id)
 );

CREATE TABLE IF NOT EXISTS gtfs_shapes (
     gtfs_version BIGINT NOT NULL REFERENCES gtfs_versions(version_id),
     shape_id VARCHAR(50) NOT NULL,
     point_sequence INT NOT NULL,
     lat DOUBLE PRECISION NOT NULL,
     lon DOUBLE PRECISION NOT NULL,
     PRIMARY KEY (gtfs_version, shape_id, point_sequence)
 );

