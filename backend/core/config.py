"""
Core configuration management for Alan's AI Assistant
Centralized settings with Pydantic validation and environment-specific configurations
"""

import os
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Main application settings with validation"""

    # Application
    app_name: str = Field(default="Alan's AI Assistant", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(
        default="development",
        description="Environment (development/production/testing)",
    )

    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Auto-reload on changes")

    # Gmail Configuration
    gmail_user: str = Field(..., description="Gmail username")
    gmail_app_pass: str = Field(..., description="Gmail app password")

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-3.5-turbo", description="OpenAI model to use"
    )
    openai_temperature: float = Field(default=0.7, description="OpenAI temperature")

    # LangSmith Configuration (Optional)
    langsmith_api_key: Optional[str] = Field(
        default=None, description="LangSmith API key"
    )
    langsmith_project: str = Field(
        default="alan-ai-assistant", description="LangSmith project name"
    )
    langsmith_project_email: Optional[str] = Field(
        default=None, description="LangSmith email project"
    )
    langsmith_project_evaluation: Optional[str] = Field(
        default=None, description="LangSmith evaluation project"
    )

    # Email Processing
    polling_interval: int = Field(
        default=300, description="Email polling interval in seconds"
    )
    max_emails_per_batch: int = Field(
        default=10, description="Maximum emails to process per batch"
    )
    max_email_size_mb: float = Field(
        default=5.0,
        description="Maximum email size to process in MB (skip larger emails)",
    )
    extract_attachments: bool = Field(
        default=True,
        description="Extract attachment content (disable for large emails)",
    )
    max_attachment_size_mb: float = Field(
        default=1.0, description="Maximum attachment size to extract in MB"
    )

    # RAG Configuration
    rag_persist_directory: str = Field(
        default="./faiss_db", description="RAG persistence directory"
    )
    rag_embedding_model: str = Field(
        default="text-embedding-3-small", description="Embedding model"
    )
    rag_max_results: int = Field(default=5, description="Maximum RAG search results")
    rag_max_index_size: int = Field(
        default=10000, description="Maximum vectors in FAISS index"
    )
    rag_use_memory_mapping: bool = Field(
        default=True, description="Use memory mapping for FAISS"
    )
    rag_batch_size: int = Field(
        default=10, description="Batch size for processing documents"
    )

    # Chunking Configuration
    chunking_recursive_chunk_size: int = Field(
        default=1000, description="Recursive splitter chunk size (tokens)"
    )
    chunking_recursive_overlap: int = Field(
        default=200, description="Recursive splitter overlap (tokens)"
    )
    chunking_sentence_overlap: int = Field(
        default=1, description="Sentence normalizer overlap (sentences)"
    )
    use_semantic_merger: bool = Field(
        default=False, description="Enable semantic merger for chunking"
    )
    chunking_semantic_embedding_model_name: str = Field(
        default="all-MiniLM-L6-v2", description="Semantic chunker embedding model name"
    )
    chunking_semantic_model_size: str = Field(
        default="small", description="Model size: small, medium, large"
    )
    chunking_semantic_unload_model_after_use: bool = Field(
        default=True,
        description="Unload model after chunking to free memory (enabled by default for memory efficiency)",
    )
    chunking_semantic_max_chunk_tokens: int = Field(
        default=500, description="Semantic chunker max chunk tokens"
    )
    chunking_semantic_similarity_threshold: float = Field(
        default=0.75, description="Semantic chunker fixed similarity threshold"
    )
    chunking_semantic_threshold_type: str = Field(
        default="fixed",
        description="Semantic chunker threshold type (fixed/percentile)",
    )
    chunking_semantic_threshold_percentile: float = Field(
        default=75.0, description="Semantic chunker percentile for dynamic thresholding"
    )
    chunking_semantic_overlap: int = Field(
        default=1, description="Semantic chunker overlap (sentences)"
    )
    chunking_semantic_embedding_batch_size: int = Field(
        default=32, description="Batch size for sentence embedding processing"
    )

    # Daily Digest
    digest_hour: int = Field(default=7, description="Daily digest hour (24h format)")
    digest_minute: int = Field(default=0, description="Daily digest minute")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:5173"], description="CORS allowed origins"
    )
    cors_credentials: bool = Field(default=True, description="CORS allow credentials")

    # Security
    secret_key: Optional[str] = Field(
        default=None, description="Secret key for JWT/sessions"
    )

    # Performance
    max_concurrent_emails: int = Field(
        default=5, description="Maximum concurrent email processing"
    )
    request_timeout: int = Field(default=30, description="Request timeout in seconds")

    # OpenMP Fix
    kmp_duplicate_lib_ok: bool = Field(
        default=True, description="Allow duplicate OpenMP libraries"
    )

    # Memory Optimization
    low_memory_mode: bool = Field(
        default=False, description="Enable aggressive memory optimizations"
    )

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting"""
        allowed_envs = ["development", "production", "testing"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of {allowed_envs}")
        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v.upper()

    @validator("openai_temperature")
    def validate_temperature(cls, v):
        """Validate OpenAI temperature"""
        if isinstance(v, str):
            v = float(v)
        if not 0.0 <= v <= 2.0:
            raise ValueError("OpenAI temperature must be between 0.0 and 2.0")
        return v

    @validator("polling_interval")
    def validate_polling_interval(cls, v):
        """Validate polling interval"""
        if isinstance(v, str):
            v = int(v)
        if v < 60:
            raise ValueError("Polling interval must be at least 60 seconds")
        return v

    @validator("digest_hour")
    def validate_digest_hour(cls, v):
        """Validate digest hour"""
        if isinstance(v, str):
            v = int(v)
        if not 0 <= v <= 23:
            raise ValueError("Digest hour must be between 0 and 23")
        return v

    @validator("digest_minute")
    def validate_digest_minute(cls, v):
        """Validate digest minute"""
        if isinstance(v, str):
            v = int(v)
        if not 0 <= v <= 59:
            raise ValueError("Digest minute must be between 0 and 59")
        return v

    @validator("chunking_semantic_model_size")
    def validate_model_size(cls, v):
        """Validate model size"""
        allowed_sizes = ["small", "medium", "large"]
        if v.lower() not in allowed_sizes:
            raise ValueError(f"Model size must be one of {allowed_sizes}")
        return v.lower()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class DevelopmentSettings(Settings):
    """Development-specific settings"""

    debug: bool = True
    reload: bool = True
    log_level: str = "DEBUG"
    environment: str = "development"


class ProductionSettings(Settings):
    """Production-specific settings"""

    debug: bool = False
    reload: bool = False
    log_level: str = "INFO"
    environment: str = "production"

    @validator("secret_key")
    def validate_secret_key(cls, v):
        """Secret key is required in production"""
        if not v:
            raise ValueError("Secret key is required in production")
        return v


class TestingSettings(Settings):
    """Testing-specific settings"""

    debug: bool = True
    environment: str = "testing"
    log_level: str = "DEBUG"
    polling_interval: int = 1  # Faster polling for tests
    rag_persist_directory: str = "./test_faiss_db"

    # Override required fields for testing
    gmail_user: str = "test@gmail.com"
    gmail_app_pass: str = "test_password"
    openai_api_key: str = "test-key"


def get_settings() -> Settings:
    """Get settings based on environment"""
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()


def setup_environment():
    """Setup environment variables and configurations"""
    # Set OpenMP fix if needed
    if settings.kmp_duplicate_lib_ok:
        os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

    # Set LangSmith environment variables if configured
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project

        if settings.langsmith_project_email:
            os.environ["LANGSMITH_PROJECT_EMAIL"] = settings.langsmith_project_email

        if settings.langsmith_project_evaluation:
            os.environ["LANGSMITH_PROJECT_EVALUATION"] = (
                settings.langsmith_project_evaluation
            )

    # Apply low memory mode optimizations
    if settings.low_memory_mode:
        # Reduce batch sizes for memory efficiency
        if settings.rag_batch_size > 5:
            settings.rag_batch_size = 5
        if settings.chunking_semantic_embedding_batch_size > 16:
            settings.chunking_semantic_embedding_batch_size = 16
        # Enable model unloading by default in low memory mode
        settings.chunking_semantic_unload_model_after_use = True
        # Use smaller model size
        if settings.chunking_semantic_model_size != "small":
            settings.chunking_semantic_model_size = "small"


# Setup environment on import
setup_environment()
