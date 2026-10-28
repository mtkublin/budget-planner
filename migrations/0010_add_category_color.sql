-- migrations/0010_add_category_color.sql
-- ADR-0047: per-category color override.
-- Adds a nullable `color TEXT` column on `categories`. NULL means "inherit
-- direction color"; set means a 6-digit lowercase hex (e.g. `#a3c2ff`).
-- Additive; no table rebuild; no FK pragma toggle.

ALTER TABLE categories
ADD COLUMN color TEXT
CHECK (color IS NULL OR color GLOB '#[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]');
