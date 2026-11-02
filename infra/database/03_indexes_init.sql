CREATE INDEX idx_timetable_matching
    ON static_timetable (service_date, vehicle_type, line, brigade);
