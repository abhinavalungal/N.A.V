"""Deterministic maritime mathematics.

Kept outside the web application on purpose: nothing here may import FastAPI,
the ORM or a provider. Inputs come in as plain values, results go out as plain
values, and every function in this package is reproducible - the same inputs
always give the same answer.

Built in Phases 3 and 4.
"""
