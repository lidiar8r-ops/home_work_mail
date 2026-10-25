from django.core.cache import cache

STATS_VERSION_KEY = "stats_version"
STATS_CACHE_TIMEOUT = 60


def get_stats_cache_version() -> int:
    version = cache.get(STATS_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(STATS_VERSION_KEY, version, None)
    return version


def bump_stats_cache() -> None:
    """Сбрасывает кеш статистики: новые ключи получают новую версию."""
    try:
        cache.incr(STATS_VERSION_KEY)
    except ValueError:
        cache.set(STATS_VERSION_KEY, 1, None)


def stats_cache_key(user) -> str:
    return (
        f"home_stats:{get_stats_cache_version()}:"
        f"{user.pk}:{int(user.is_manager)}"
    )


def statistics_totals_key(user) -> str:
    return (
        f"statistics_totals:{get_stats_cache_version()}:"
        f"{user.pk}:{int(user.is_manager)}"
    )
