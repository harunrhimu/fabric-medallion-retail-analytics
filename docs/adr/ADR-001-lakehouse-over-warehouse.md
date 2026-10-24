# ADR-001: Lakehouse over a standalone warehouse

**Status:** accepted · 2026-10-24

## Context

The system needs raw landing, cleansed tables, a dimensional model and a
Direct Lake semantic model. The alternative was a standalone SQL warehouse
(Synapse serverless / SQL DB) with files moved by an external tool.

## Decision

Store everything in one Fabric Lakehouse (OneLake) as Delta tables and run
transformations as PySpark notebooks attached to that Lakehouse.

## Consequences

- Bronze can keep raw files and raw tables together; Silver/Gold are table
  rebuilds over the same storage - no extract/move step between layers.
- Direct Lake reads Delta files directly, so the semantic model has no
  import/refresh copy of the data to manage.
- PySpark gives the transformation code a portable shape (the same skills the
  job market asks for), while SQL consumers still get a T-SQL endpoint over Gold.
- Cost model is capacity-based rather than per-query - a tradeoff accepted for
  a portfolio workload on trial capacity.

## Alternatives rejected

- **Files + serverless SQL only:** cheaper, but no PySpark, no Delta
  time-travel, and Direct Lake would not be the natural fit.
- **Standalone warehouse + external ingest tool:** adds a second platform to
  operate and a sync step between layers for no benefit at this scale.
