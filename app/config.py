"""Configurações da aplicação, carregadas de variáveis de ambiente / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações lidas do ambiente ou do arquivo .env."""

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    model_effort: str = "high"
    max_output_tokens: int = 32000

    # Chave pública da API Pública do DataJud (CNJ). Não é segredo: o CNJ a
    # publica para acesso aberto. Pode ser sobrescrita por variável de ambiente.
    datajud_api_key: str = (
        "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
