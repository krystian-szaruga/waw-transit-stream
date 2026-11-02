CREATE TABLE IF NOT EXISTS static_timetable (
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
     PRIMARY KEY (service_date, trip_id, stop_sequence)
 );

CREATE INDEX idx_timetable_matching
    ON static_timetable (service_date, vehicle_type, line, brigade);
