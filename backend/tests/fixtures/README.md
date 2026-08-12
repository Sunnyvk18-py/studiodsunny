# Test fixtures

- `prod_shape.sql` — scrubbed INSERT-only dump for migration-over-data tests. Regenerate via `scripts/generate_prod_shape.py` then `scripts/scrub_dump.py`. **Never commit a raw dump.**
- `hostile_seed.py` — deliberately difficult valid data for render/timing tests.
