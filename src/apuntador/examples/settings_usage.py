"""
Ejemplos de cómo usar settings en diferentes contextos.

Este archivo demuestra las dos formas de acceder a la configuración:
1. Dependency injection (FastAPI routers/endpoints)
2. Importación directa (services, utils, scripts)
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apuntador.config import Settings, get_settings, settings

# ============================================================================
# OPCIÓN 1: Usando Dependency Injection (Recomendado en endpoints)
# ============================================================================

router_di = APIRouter(tags=["ejemplos-dependency-injection"])


@router_di.get("/example/di/project-info")
async def get_project_info_di(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """
    Ejemplo: Usar Depends(get_settings) en endpoints FastAPI.

    Ventajas:
    - FastAPI refresca automáticamente si cambian las env vars
    - Fácil de mockear en tests
    - Patrón estándar de FastAPI
    """
    return {
        "project_name": settings.project_name,
        "version": settings.project_version,
        "debug": str(settings.debug),
    }


@router_di.get("/example/di/oauth-config")
async def get_oauth_config_di(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Ejemplo: Acceder a configuración OAuth con dependency injection."""
    return {
        "google_configured": bool(settings.google_client_id),
        "dropbox_configured": bool(settings.dropbox_client_id),
        "onedrive_configured": bool(settings.onedrive_client_id),
    }


# ============================================================================
# OPCIÓN 2: Importación directa (Para código fuera de FastAPI)
# ============================================================================

router_direct = APIRouter(tags=["ejemplos-importacion-directa"])


@router_direct.get("/example/direct/project-info")
async def get_project_info_direct() -> dict[str, str]:
    """
    Ejemplo: Usar instancia global 'settings' directamente.

    Ventajas:
    - Más simple, no necesitas Depends()
    - Útil en código que no es FastAPI (utils, services, scripts)

    Desventajas:
    - No se refresca automáticamente (cacheado)
    - Más difícil de mockear en tests
    """
    return {
        "project_name": settings.project_name,
        "version": settings.project_version,
        "debug": str(settings.debug),
    }


@router_direct.get("/example/direct/cors-config")
async def get_cors_config_direct() -> dict[str, any]:
    """Ejemplo: Usar métodos helper de settings."""
    return {
        "allowed_origins": settings.get_allowed_origins(),
        "allowed_methods": settings.get_cors_allowed_methods(),
        "allowed_headers": settings.get_cors_allowed_headers(),
    }


# ============================================================================
# OPCIÓN 3: Llamando get_settings() en código no-FastAPI
# ============================================================================


def example_service_function() -> str:
    """
    Ejemplo: Usar settings en una función de servicio.

    Esta es la forma recomendada para código fuera de FastAPI endpoints.
    """
    # Opción A: Usar instancia global (más simple)
    project_name = settings.project_name

    # Opción B: Llamar get_settings() (equivalente, pero más explícito)
    current_settings = get_settings()
    project_version = current_settings.project_version

    return f"{project_name} v{project_version}"


class ExampleService:
    """
    Ejemplo: Usar settings en una clase de servicio.
    """

    def __init__(self):
        """Opción 1: Inicializar con instancia global."""
        self.config = settings

    @classmethod
    def from_settings(cls, settings: Settings):
        """Opción 2: Inyectar settings como parámetro."""
        instance = cls()
        instance.config = settings
        return instance

    def get_oauth_providers(self) -> list[str]:
        """Ejemplo: Método que usa la configuración."""
        providers = []

        if self.config.google_client_id:
            providers.append("googledrive")

        if self.config.dropbox_client_id:
            providers.append("dropbox")

        if self.config.onedrive_client_id:
            providers.append("onedrive")

        return providers


# ============================================================================
# OPCIÓN 4: Refrescar settings (en tests o desarrollo)
# ============================================================================


def example_refresh_settings():
    """
    Ejemplo: Limpiar cache para refrescar settings.

    Útil en:
    - Tests que cambian variables de entorno
    - Desarrollo con hot reload
    - Scripts que modifican el .env
    """
    # Limpiar cache
    get_settings.cache_clear()

    # Obtener nueva instancia con valores actualizados
    fresh_settings = get_settings()

    return fresh_settings


# ============================================================================
# RESUMEN: ¿Cuándo usar cada opción?
# ============================================================================

"""
1. Dependency Injection (Depends):
   ✅ En FastAPI endpoints/routers
   ✅ Cuando necesitas testing fácil
   ✅ Para auto-refresh en desarrollo
   ❌ No disponible fuera de FastAPI

2. Instancia global (settings):
   ✅ En servicios, utils, scripts
   ✅ Código que no es FastAPI
   ✅ Más simple y directo
   ❌ Cacheado (no auto-refresh)

3. Llamar get_settings():
   ✅ Equivalente a usar 'settings'
   ✅ Más explícito
   ✅ Puedes limpiar cache si necesitas

Recomendación por contexto:
- FastAPI routers → Depends(get_settings)
- Services/utils → import settings
- Scripts standalone → get_settings() o settings
- Tests → Depends() + mocking
"""
