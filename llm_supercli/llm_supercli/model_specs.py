"""
Model specifications and pricing information.
Updated: 2025-01-28
"""

from typing import Dict, Any

# Gemini Model Specifications
GEMINI_MODEL_SPECS = {
    "auto": {
        "display_name": "Auto (Gemini chooses best model)",
        "description": "Let Gemini automatically choose the best model for your task",
        "context_window": 1_048_576,  # 1M tokens (varies by selected model)
        "max_output_tokens": 8192,
        "pricing": {
            "input_per_1m": 0.10,  # Estimated average
            "output_per_1m": 0.40,
            "currency": "USD"
        },
        "features": ["text", "code", "vision", "audio"],
        "rate_limit_rpm": 1500,
        "free_tier": True,
    },
    "gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro",
        "description": "Best for complex reasoning, coding, and long-context workloads",
        "context_window": 256_000,  # 256K tokens (~190K words)
        "max_output_tokens": 8192,
        "pricing": {
            "input_per_1m": 1.25,  # ≤200K tokens
            "input_per_1m_long": 2.50,  # >200K tokens
            "output_per_1m": 10.00,
            "currency": "USD"
        },
        "features": ["text", "code", "vision", "audio", "thinking"],
        "rate_limit_rpm": 1500,
        "free_tier": True,
    },
    "gemini-2.5-flash": {
        "display_name": "Gemini 2.5 Flash",
        "description": "Fast chat, summaries, large-scale processing, low-latency tasks",
        "context_window": 1_048_576,  # 1M tokens (~750K words)
        "max_output_tokens": 8192,
        "pricing": {
            "input_per_1m": 0.10,  # text/image/video
            "input_audio_per_1m": 0.70,
            "output_per_1m": 0.40,
            "currency": "USD"
        },
        "features": ["text", "code", "vision", "audio", "thinking"],
        "rate_limit_rpm": 1500,
        "free_tier": True,
    },
    "gemini-2.5-flash-lite": {
        "display_name": "Gemini 2.5 Flash-Lite",
        "description": "Most cost-efficient, optimized for high-throughput, low-latency workloads",
        "context_window": 1_048_576,  # 1M tokens
        "max_output_tokens": 8192,
        "pricing": {
            "input_per_1m": 0.10,  # text/image/video
            "input_audio_per_1m": 0.30,
            "output_per_1m": 0.40,
            "currency": "USD"
        },
        "features": ["text", "code", "vision", "audio"],
        "rate_limit_rpm": 1500,
        "free_tier": True,
    },
}

# Qwen Model Specifications
QWEN_MODEL_SPECS = {
    "coder-model": {
        "display_name": "Qwen Coder (qwen3-coder-plus)",
        "description": "Latest Qwen Coder model from Alibaba Cloud ModelStudio",
        "context_window": 128_000,  # 128K tokens
        "max_output_tokens": 8192,
        "pricing": {
            "input_per_1m": 1.00,
            "output_per_1m": 5.00,
            "currency": "USD",
            "note": "Free via Qwen Code CLI: 2,000 requests/day, no token limits"
        },
        "features": ["text", "code"],
        "rate_limit_rpm": 60,
        "free_tier": True,
        "free_tier_limits": {
            "requests_per_day": 2000,
            "requests_per_minute": 60,
            "token_limit": None  # No limit
        },
    },
    "vision-model": {
        "display_name": "Qwen Vision (qwen3-vl-plus)",
        "description": "Latest Qwen Vision model from Alibaba Cloud ModelStudio",
        "context_window": 7_500,  # 7.5K tokens
        "max_output_tokens": 2048,
        "pricing": {
            "input_per_1m": 0.21,
            "output_per_1m": 0.63,
            "currency": "USD",
            "note": "Free via Qwen Code CLI"
        },
        "features": ["text", "code", "vision"],
        "rate_limit_rpm": 60,
        "free_tier": True,
        "free_tier_limits": {
            "requests_per_day": 2000,
            "requests_per_minute": 60,
            "token_limit": None
        },
    },
}


def get_model_info(provider: str, model: str) -> Dict[str, Any]:
    """Get detailed information about a specific model."""
    if provider.lower() == "gemini":
        return GEMINI_MODEL_SPECS.get(model, {})
    elif provider.lower() == "qwen":
        return QWEN_MODEL_SPECS.get(model, {})
    return {}


def format_model_info(provider: str, model: str) -> str:
    """Format model information for display."""
    info = get_model_info(provider, model)
    if not info:
        return f"No information available for {provider}/{model}"
    
    lines = [
        f"📊 {info.get('display_name', model)}",
        f"",
        f"📝 {info.get('description', 'N/A')}",
        f"",
        f"💾 Context Window: {info.get('context_window', 0):,} tokens",
        f"📤 Max Output: {info.get('max_output_tokens', 0):,} tokens",
        f"",
    ]
    
    # Pricing
    pricing = info.get('pricing', {})
    if pricing:
        lines.append("💰 Pricing:")
        lines.append(f"   Input:  ${pricing.get('input_per_1m', 0):.2f} / 1M tokens")
        if 'input_per_1m_long' in pricing:
            lines.append(f"   Input (>200K): ${pricing.get('input_per_1m_long', 0):.2f} / 1M tokens")
        if 'input_audio_per_1m' in pricing:
            lines.append(f"   Audio Input: ${pricing.get('input_audio_per_1m', 0):.2f} / 1M tokens")
        lines.append(f"   Output: ${pricing.get('output_per_1m', 0):.2f} / 1M tokens")
        if 'note' in pricing:
            lines.append(f"   Note: {pricing['note']}")
        lines.append("")
    
    # Free tier
    if info.get('free_tier'):
        lines.append("✅ Free Tier Available")
        free_limits = info.get('free_tier_limits')
        if free_limits:
            lines.append(f"   • {free_limits.get('requests_per_day', 'N/A')} requests/day")
            lines.append(f"   • {free_limits.get('requests_per_minute', 'N/A')} requests/minute")
            if free_limits.get('token_limit'):
                lines.append(f"   • {free_limits['token_limit']:,} tokens limit")
            else:
                lines.append(f"   • No token limit")
        lines.append("")
    
    # Features
    features = info.get('features', [])
    if features:
        lines.append(f"🎯 Features: {', '.join(features)}")
        lines.append("")
    
    # Rate limits
    rpm = info.get('rate_limit_rpm')
    if rpm:
        lines.append(f"⚡ Rate Limit: {rpm} requests/minute")
    
    return "\n".join(lines)
