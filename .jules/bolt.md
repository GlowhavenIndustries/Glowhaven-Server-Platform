## 2026-03-31 - Avoid `__import__` and redundant clock calls in hot status calculation loops

**Learning:** Dynamic module lookups like `__import__('datetime')` and calling system time (`utcnow()`) inside tight loops (like fleet status evaluation for every server) incur significant micro-overhead. Furthermore, converting `sqlite3.Row` float values via `float(...)` and constructing Python list objects for `max(...)` adds unnecessary allocations.

**Action:**
1. Always import modules top-level.
2. Allow functions evaluating row status/timestamps to accept a pre-computed `now` timestamp when iterating over collections.
3. Use direct short-circuit logical operators (`a >= T or b >= T or c >= T`) over `max([a, b, c]) >= T`.
