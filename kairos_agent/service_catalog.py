"""Service catalog — resolve which sources to query for an incident.

Maps services to their log sources and dependencies, enabling
dependency-aware context assembly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from kairos_agent.config import KairosConfig, LogSource

logger = logging.getLogger("kairos_agent")


@dataclass
class ResolvedSource:
    """A LogSource tagged with its provenance."""

    log_source: LogSource
    origin_service: str
    relationship: str  # "direct" or "dependency"


def _resolve_source_ref(
    ref: str,
    log_sources: list[LogSource],
) -> LogSource | None:
    """Resolve a source reference string to a LogSource.

    Resolution order:
    1. Match by LogSource.name (exact)
    2. Inline file pattern: "file:/path/to/glob"
    3. Match by LogSource.type (first match)
    """
    # 1. Match by name
    for ls in log_sources:
        if ls.name and ls.name == ref:
            return ls

    # 2. Inline file pattern
    if ref.startswith("file:"):
        return LogSource(type="file", path=ref[5:])

    # 3. Match by type
    for ls in log_sources:
        if ls.type == ref:
            return ls

    logger.warning("Could not resolve source reference: '%s'", ref)
    return None


def resolve_sources_for_alert(
    service_name: str,
    config: KairosConfig,
) -> list[ResolvedSource]:
    """Resolve which sources to query for an alerting service.

    If the service is in the catalog, returns its specific sources
    plus sources from its direct dependencies (depth 1 only).

    If the service is NOT in the catalog, falls back to all
    configured log_sources (v0.2 behavior).
    """
    service = config.services.get(service_name)

    if service is None:
        # Fallback: no catalog entry, use all sources
        return [
            ResolvedSource(
                log_source=ls,
                origin_service=service_name,
                relationship="direct",
            )
            for ls in config.log_sources
        ]

    resolved: list[ResolvedSource] = []
    visited: set[str] = set()

    # Resolve direct sources
    visited.add(service_name)
    for ref in service.sources:
        ls = _resolve_source_ref(ref, config.log_sources)
        if ls:
            resolved.append(ResolvedSource(
                log_source=ls,
                origin_service=service_name,
                relationship="direct",
            ))

    # Resolve dependency sources (depth 1 only)
    for dep_name in service.depends_on:
        if dep_name in visited:
            logger.warning(
                "Circular dependency detected: %s <-> %s — skipping",
                service_name, dep_name,
            )
            continue
        visited.add(dep_name)

        dep_service = config.services.get(dep_name)
        if dep_service is None:
            logger.warning(
                "Dependency '%s' not in service catalog — skipping",
                dep_name,
            )
            continue

        for ref in dep_service.sources:
            ls = _resolve_source_ref(ref, config.log_sources)
            if ls:
                resolved.append(ResolvedSource(
                    log_source=ls,
                    origin_service=dep_name,
                    relationship="dependency",
                ))

    if not resolved:
        logger.warning(
            "No sources resolved for service '%s' — falling back to all sources",
            service_name,
        )
        return [
            ResolvedSource(
                log_source=ls,
                origin_service=service_name,
                relationship="direct",
            )
            for ls in config.log_sources
        ]

    return resolved
