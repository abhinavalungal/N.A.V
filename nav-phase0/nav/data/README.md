# Data

`seed/` - deterministic seed data loaded into a fresh database: companies,
users, vessels, voyages, historical voyages, fuel prices. Added in Phase 2 and
extended as later phases need it.

`mock/` - fixtures behind the mock providers: weather observations and
forecasts, route geometry, fuel prices. Added in Phase 3.

Two rules for anything placed here. It is synthetic - no real customer or
commercially confidential data, and IMO numbers come from a reserved test
range. And it is labelled: data that reaches the console through a mock
provider is marked as mock there, so a demonstration is never mistaken for a
live reading.
