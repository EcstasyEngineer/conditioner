import os
from dataclasses import dataclass

@dataclass
class Environment:
    """Environment-specific configuration."""
    name: str
    command_prefix: str
    status_prefix: str
    test_channel_id: int = None

# Environment configurations
ENVIRONMENTS = {
    'production': Environment(
        name='production',
        command_prefix='!',
        status_prefix='',
        test_channel_id=None
    ),
    'development': Environment(
        name='development',
        command_prefix='!!',  # Different prefix for dev
        status_prefix='[DEV] ',
        test_channel_id=1234567890  # Your test channel ID
    )
}

def get_environment():
    """Get current environment configuration."""
    env_name = os.getenv('BOT_ENV', 'development').lower()
    return ENVIRONMENTS.get(env_name, ENVIRONMENTS['development'])