""" Config file for the AI Tutoring System app """

llm = {
    "model_name": "gpt-4.1-mini",
    "temperature": 0.7,
    "max_tokens": 1500,
}

default_difficulty = "easy"


class Config:
    """Configuration class for the AI Tutoring System."""
    
    def __init__(self):
        self.llm = llm
        self.default_difficulty = default_difficulty
        self.model_name = llm["model_name"]
        self.temperature = llm["temperature"]
        self.max_tokens = llm["max_tokens"]


class ConfigManager:
    """Singleton config manager."""
    
    def __init__(self):
        self.config = Config()
    
    def get_config(self):
        """Get the configuration object."""
        return self.config


# Global config manager instance
config_manager = ConfigManager()
