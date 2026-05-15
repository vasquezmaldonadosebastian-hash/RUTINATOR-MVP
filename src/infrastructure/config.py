"""
Configuración centralizada usando pydantic-settings.
Carga variables de entorno desde .env
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Telegram
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")

    # Rutas
    data_dir: Path = Field(default=Path(__file__).parent.parent.parent / "data")
    ejercicios_csv_path: Path | None = Field(default=None)

    # Configuración de logging
    log_level: str = Field(default="INFO")

    # Configuración de PDFs
    pdf_margin: float = Field(default=0.6)
    pdf_dpi: int = Field(default=150)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-configurar ruta del CSV si no se provee
        if self.ejercicios_csv_path is None:
            object.__setattr__(self, 'ejercicios_csv_path', self.data_dir / "ejercicios.csv")

    @property
    def csv_path(self) -> Path:
        """Ruta al CSV de ejercicios."""
        return Path(self.ejercicios_csv_path)


@lru_cache
def get_settings() -> Settings:
    """Obtiene configuración cachingada (singleton)."""
    return Settings()


# Instancia global de configuración
settings = get_settings()
