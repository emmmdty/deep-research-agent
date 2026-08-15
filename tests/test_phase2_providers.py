"""Phase 02 provider routing and config contract tests."""

from __future__ import annotations


def test_settings_exposes_all_required_provider_profiles():
    """Settings 应为四类 provider 暴露完整 profile。"""
    from configs.settings import Settings

    profiles = Settings().get_provider_profiles()

    assert set(profiles) == {"openai", "anthropic", "openai_compatible", "anthropic_compatible"}
    assert profiles["openai"].provider_type == "openai"
    assert profiles["anthropic"].provider_type == "anthropic"
    assert profiles["openai_compatible"].provider_type == "openai_compatible"
    assert profiles["anthropic_compatible"].provider_type == "anthropic_compatible"


def test_settings_maps_legacy_provider_alias_to_openai_compatible():
    """旧 provider 名应在配置层归一到兼容层语义。"""
    from configs.settings import Settings

    settings = Settings(llm_provider="minimax")

    assert settings.llm_provider.value == "openai_compatible"


def test_provider_router_supports_manual_routing():
    """manual routing 应按显式 provider profile 解析。"""
    from configs.settings import Settings
    from deep_research_agent.providers import ProviderRouter, ProviderRouteRequest

    router = ProviderRouter(Settings())
    route = router.route(
        ProviderRouteRequest(
            task_role="planning",
            provider_profile="anthropic",
            routing_mode="manual",
        )
    )

    assert route.profile.name == "anthropic"
    assert route.profile.provider_type == "anthropic"


def test_provider_router_auto_routing_prefers_reasoning_for_planning():
    """planning 应优先选择 reasoning-capable provider。"""
    from configs.settings import Settings
    from deep_research_agent.providers import ProviderRouter, ProviderRouteRequest

    router = ProviderRouter(Settings())
    route = router.route(ProviderRouteRequest(task_role="planning", routing_mode="auto"))

    assert route.profile.name == "openai_compatible"
    assert route.profile.capabilities.reasoning is True


def test_provider_router_auto_routing_prefers_cross_vendor_judge():
    """judge 路由应偏向跨 vendor 选择，而不是沿用当前 provider。"""
    from configs.settings import Settings
    from deep_research_agent.providers import ProviderRouter, ProviderRouteRequest

    router = ProviderRouter(Settings(llm_provider="openai"))
    route = router.route(
        ProviderRouteRequest(
            task_role="judge",
            routing_mode="auto",
            current_provider="openai",
        )
    )

    assert route.profile.name == "anthropic"


def test_llm_provider_message_conversion_preserves_multi_turn_roles():
    """chat/achat 的消息转换必须保留 assistant 回合，不得压平成单轮。"""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    from deep_research_agent.providers.clients import _to_langchain_messages

    converted = _to_langchain_messages(
        [
            {"role": "system", "content": "你是研究员"},
            {"role": "user", "content": "问题一"},
            {"role": "assistant", "content": "回答一"},
            {"role": "user", "content": "问题二"},
        ]
    )

    assert [type(message) for message in converted] == [
        SystemMessage,
        HumanMessage,
        AIMessage,
        HumanMessage,
    ]
    assert converted[2].content == "回答一"
