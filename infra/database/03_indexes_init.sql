CREATE INDEX idx_timetable_matching
    ON static_timetable (gtfs_version, service_date, vehicle_type, line, brigade);

CREATE INDEX idx_shapes_route
    ON gtfs_trip_shapes (gtfs_version, shape_id);

CREATE INDEX idx_timetable_matching
    ON static_timetable (gtfs_version, service_date, vehicle_type, line, brigade);
