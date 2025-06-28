"""
Hume EVI Configuration Service
Manages EVI configurations for Study Buddy voice chat integration
"""

import logging
from typing import Optional, Dict, Any
from hume.client import AsyncHumeClient, HumeClient
from app.config import settings

logger = logging.getLogger(__name__)

# Study Buddy EVI Configuration Template
STUDY_BUDDY_EVI_CONFIG = {
    "name": "Study Buddy Voice Assistant",
    "description": "AI-powered study companion with document-aware voice chat",
    "voice": {
        "type": "Evi2",
        "provider": "HUME_AI",
        "name": "ITO",  # Calm, clear voice suitable for educational content
    },
    "language_model": {
        "model_provider": "ANTHROPIC",
        "model_resource": "claude-3-haiku-20240307",
        "temperature": 0.7,
        "max_tokens": 150,  # Shorter responses for voice
        "system_prompt": """You are Study Buddy, an AI study companion. You help students understand their uploaded course materials through voice conversation.

Key guidelines:
- Keep responses concise and clear for voice delivery (under 150 words)
- Use conversational, encouraging tone
- When referencing sources, mention them naturally: "According to your lecture notes..." or "Based on the textbook chapter..."
- Focus on educational explanations and insights
- Ask follow-up questions to encourage deeper learning
- If you don't know something from the materials, say so clearly

Your goal is to help students learn effectively through natural voice conversation about their documents."""
    },
    "tools": [
        {
            "type": "built_in",
            "name": "web_search",
            "enabled": False  # We use our own RAG system
        }
    ],
    "event_messages": {
        "on_new_chat": {
            "enabled": True,
            "text": "Hi there! I'm Study Buddy, your AI study companion. I can help you understand your uploaded course materials. What would you like to explore today?"
        },
        "on_inactivity_timeout": {
            "enabled": True,
            "text": "I'm still here when you're ready to continue studying!",
            "timeout_seconds": 60
        },
        "on_max_duration_timeout": {
            "enabled": True,
            "text": "We've been chatting for a while! Feel free to start a new session when you're ready to continue.",
            "timeout_seconds": 1800  # 30 minutes
        }
    },
    "builtin_tools": [],
    "response_preferences": {
        "response_length": "short",  # Better for voice
        "response_style": "conversational",
        "include_citations": True
    }
}

async def get_or_create_study_buddy_config() -> str:
    """
    Get existing Study Buddy EVI config or create a new one
    
    Returns:
        EVI configuration ID
    """
    if not settings.HUME_API_KEY:
        raise ValueError("HUME_API_KEY not configured")
    
    try:
        client = AsyncHumeClient(api_key=settings.HUME_API_KEY)
        
        # First, list existing configs once so we can reuse the result
        existing_configs_pager = await client.empathic_voice.configs.list_configs()
        existing_ids = {}
        async for cfg in existing_configs_pager:
            existing_ids[cfg.id] = cfg  # keep reference for later

        # If we have a stored ID, prefer it if it still exists
        if settings.HUME_EVI_CONFIG_ID and settings.HUME_EVI_CONFIG_ID in existing_ids:
            logger.info(f"Using existing EVI config by stored ID: {settings.HUME_EVI_CONFIG_ID}")
            return settings.HUME_EVI_CONFIG_ID

        # If a config with our standard name exists, reuse it
        for cfg in existing_ids.values():
            if cfg.name == STUDY_BUDDY_EVI_CONFIG["name"]:
                logger.info(f"Reusing existing EVI config found by name: {cfg.id}")
                settings.HUME_EVI_CONFIG_ID = cfg.id
                return cfg.id
        
        # Create new configuration
        logger.info("Creating new Study Buddy EVI configuration...")
        config_id = await create_study_buddy_config(client)
        
        # Store config ID for future use (in production, save to database)
        settings.HUME_EVI_CONFIG_ID = config_id
        logger.info(f"Created new EVI config: {config_id}")
        
        return config_id
        
    except Exception as e:
        logger.error(f"Error managing EVI configuration: {e}")
        # Fallback to default config
        logger.warning("Using default EVI configuration")
        return None

async def create_study_buddy_config(client: AsyncHumeClient) -> str:
    """
    Create a new Study Buddy EVI configuration
    
    Args:
        client: Hume client instance
        
    Returns:
        Configuration ID
    """
    try:
        system_prompt_text = STUDY_BUDDY_EVI_CONFIG["language_model"]["system_prompt"]
        response = await client.empathic_voice.configs.create_config(
            evi_version="1",
            name=STUDY_BUDDY_EVI_CONFIG["name"],
            voice=STUDY_BUDDY_EVI_CONFIG["voice"],
            language_model={
                "model_provider": STUDY_BUDDY_EVI_CONFIG["language_model"]["model_provider"],
                "model_resource": STUDY_BUDDY_EVI_CONFIG["language_model"]["model_resource"],
                "temperature": STUDY_BUDDY_EVI_CONFIG["language_model"]["temperature"],
                "max_tokens": STUDY_BUDDY_EVI_CONFIG["language_model"]["max_tokens"],
            },
            prompt={"text": system_prompt_text},
            event_messages=STUDY_BUDDY_EVI_CONFIG["event_messages"]
        )
        return response.id
    except Exception as e:
        # Handle duplicate config name (status 409)
        if "409" in str(e):
            logger.info("Config already exists, searching for existing one...")
            pager = await client.empathic_voice.configs.list_configs()
            async for cfg in pager:
                if cfg.name == STUDY_BUDDY_EVI_CONFIG["name"]:
                    return cfg.id
        logger.error(f"Failed to create EVI configuration: {e}")
        raise

async def get_evi_config(config_id: str) -> Optional[Dict[str, Any]]:
    """Look up a config by id using list_configs fallback (SDK has no .get for async)."""
    try:
        client = AsyncHumeClient(api_key=settings.HUME_API_KEY)
        pager = await client.empathic_voice.configs.list_configs()
        # pager may be AsyncPager; iterate over items
        async for cfg in pager:
            if cfg.id == config_id:
                return cfg.dict()
        return None
    except Exception as e:
        logger.error(f"Error retrieving EVI config {config_id}: {e}")
        return None

async def update_study_buddy_config(config_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update an existing EVI configuration
    
    Args:
        config_id: Configuration ID to update
        updates: Dictionary of fields to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = HumeClient(api_key=settings.HUME_API_KEY)
        
        await client.empathic_voice.configs.update(
            id=config_id,
            **updates
        )
        
        logger.info(f"Updated EVI config {config_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating EVI config {config_id}: {e}")
        return False

async def delete_evi_config(config_id: str) -> bool:
    """
    Delete an EVI configuration
    
    Args:
        config_id: Configuration ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = HumeClient(api_key=settings.HUME_API_KEY)
        
        await client.empathic_voice.configs.delete(id=config_id)
        
        logger.info(f"Deleted EVI config {config_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting EVI config {config_id}: {e}")
        return False

def get_study_buddy_config_template() -> Dict[str, Any]:
    """
    Get the Study Buddy EVI configuration template
    
    Returns:
        Configuration template dictionary
    """
    return STUDY_BUDDY_EVI_CONFIG.copy()

def validate_evi_config(config: Dict[str, Any]) -> bool:
    """
    Validate an EVI configuration structure
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["name", "voice", "language_model"]
    
    for field in required_fields:
        if field not in config:
            logger.error(f"Missing required field in EVI config: {field}")
            return False
    
    # Validate voice configuration
    if "name" not in config["voice"]:
        logger.error("Missing voice name in EVI config")
        return False
    
    # Validate language model configuration
    lm_config = config["language_model"]
    required_lm_fields = ["model_resource", "system_prompt"]
    
    for field in required_lm_fields:
        if field not in lm_config:
            logger.error(f"Missing language model field: {field}")
            return False
    
    logger.info("EVI configuration validation successful")
    return True

# Convenience function for getting optimal voice settings
def get_recommended_voice_settings() -> Dict[str, Any]:
    """
    Get recommended voice settings for Study Buddy
    
    Returns:
        Recommended voice configuration
    """
    return {
        "voice_name": "ITO",  # Clear, professional voice
        "speaking_rate": 1.0,  # Normal speed
        "pitch": 0.0,  # Neutral pitch
        "emphasis": "moderate",  # Moderate emphasis for engagement
    }