"""Repository layer — the only path between services and SQL.

See ADR-0022 for the discipline (soft-delete default, audit-in-same-tx,
pure functions, no classes beyond frozen dataclasses).
"""
