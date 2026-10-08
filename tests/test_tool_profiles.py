"""GMA_TOOL_PROFILE: curated tool subsets for MCP clients."""

import pytest

from src.tool_profiles import CORE_TOOLS, STANDARD_TOOLS, resolve_profile, tier_of, visible_tools


@pytest.fixture
def server():
    import src.server as server

    yield server
    server.apply_tool_profile("full")  # never leak a reduced profile into other tests


def test_profile_members_are_real_tools(server):
    registered = set(server._ALL_TOOLS)
    assert not (STANDARD_TOOLS - registered), sorted(STANDARD_TOOLS - registered)


def test_profiles_nest_and_shrink(server):
    registered = set(server._ALL_TOOLS)
    core = visible_tools("core", registered)
    standard = visible_tools("standard", registered)
    full = visible_tools("full", registered)
    assert core < standard < full == registered
    assert len(core) <= 30
    assert len(standard) <= 120


def test_one_tool_per_overlap_cluster_in_small_profiles():
    for cluster in (
        {"get_executor_state", "get_executor_status", "get_executor_detail"},
        {"check_pool_slot_availability", "check_pool_availability"},
        {"diff_cues", "compare_cue_values"},
        {"master_control", "control_special_master"},
    ):
        assert len(cluster & STANDARD_TOOLS) == 1, cluster


def test_apply_core_hides_tools_from_clients_but_not_from_the_agent(server):
    assert server.apply_tool_profile("core") == "core"
    assert set(server.mcp._tool_manager._tools) == CORE_TOOLS & set(server._ALL_TOOLS)
    registry = server._build_tool_registry()
    assert "store_object" in registry  # agent workflows still have everything
    assert len(registry) == len(server._ALL_TOOLS)


def test_unknown_profile_falls_back_to_full():
    profile, warning = resolve_profile("tiny")
    assert profile == "full"
    assert "tiny" in warning


def test_default_is_full():
    assert resolve_profile(None) == ("full", None)


def test_tier_of():
    assert tier_of("send_raw_command") == "core"
    assert tier_of("store_object") == "standard"
    assert tier_of("recluster_tools") == "full"


def test_tiers_resource_is_generated_from_code(server):
    text = server.resource_tool_surface_tiers()
    assert "## core" in text and "## standard" in text and "## full" in text
    assert f"## full — {len(server._ALL_TOOLS)} tools" in text
