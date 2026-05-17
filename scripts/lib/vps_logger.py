"""DEPRECATED: name retained for compatibility. Re-exports SupabaseSink.

The old FastAPI/VPS observability sink at eduplugin.birdzeye.in has been
replaced by direct Supabase writes into the Edustack project's
`eduplugin_events` table. The Stop hook for chat shipping and the
debug viewer also live in Edustack now (the EduStack-Platform Next.js
app's /admin/eduplugin/runs route).

Why: the FastAPI approach required GHCR image hosting + Hostinger MCP
deploys + TLS + per-user token bootstrap. Supabase removes all of it
while reusing infrastructure the user already runs.

Callers who imported VPSLogger from this module continue to work — the
name is aliased to SupabaseSink with identical method signatures.
"""
from __future__ import annotations
from scripts.lib.supabase_sink import SupabaseSink as VPSLogger  # noqa: F401

__all__ = ["VPSLogger"]
