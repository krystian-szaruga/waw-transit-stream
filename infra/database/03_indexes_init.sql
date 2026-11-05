CREATE INDEX idx_timetable_matching
    ON static_timetable (gtfs_version, service_date, vehicle_type, line, brigade);
