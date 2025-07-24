"""Cache service implementation using Redis and memory cache."""

import hashlib
import json
from typing import Any, Optional

from aiocache import Cache
from aiocache.serializers import PickleSerializer

from ..config import get_settings


class CacheService:
    """Multi-level cache service with memory and Redis backend."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache service."""
        settings = get_settings()
        self.enabled = settings.enable_cache
        self.default_ttl = settings.cache_ttl_seconds
        
        if not self.enabled:
            self.memory_cache = None
            self.redis_cache = None
            return
        
        # L1: Memory cache for hot data
        self.memory_cache = Cache(Cache.MEMORY)
        
        # L2: Redis cache for persistence
        if redis_url:
            self.redis_cache = Cache(
                Cache.REDIS,
                endpoint=redis_url,
                serializer=PickleSerializer(),
                ttl=self.default_ttl
            )
        else:
            self.redis_cache = None
    
    async def initialize(self) -> None:
        """Initialize cache connections."""
        # Cache initialization is handled in __init__
        pass
    
    async def close(self) -> None:
        """Close cache connections."""
        if self.memory_cache:
            await self.memory_cache.close()
        if self.redis_cache:
            await self.redis_cache.close()
    
    def _cache_key(self, prefix: str, **params) -> str:
        """Generate stable cache key from parameters."""
        # Sort parameters for consistent key generation
        key_data = json.dumps(params, sort_keys=True)
        hash_key = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None
        
        # Check L1 (memory)
        result = await self.memory_cache.get(key)
        if result is not None:
            return result
        
        # Check L2 (Redis)
        if self.redis_cache:
            result = await self.redis_cache.get(key)
            if result is not None:
                # Backfill to L1
                await self.memory_cache.set(key, result, ttl=60)
                return result
        
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> None:
        """Set value in cache."""
        if not self.enabled:
            return
        
        ttl = ttl or self.default_ttl
        
        # Set in L1 (memory) with shorter TTL
        await self.memory_cache.set(key, value, ttl=min(ttl, 300))
        
        # Set in L2 (Redis)
        if self.redis_cache:
            await self.redis_cache.set(key, value, ttl=ttl)
    
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        if not self.enabled:
            return
        
        await self.memory_cache.delete(key)
        if self.redis_cache:
            await self.redis_cache.delete(key)
    
    async def clear(self, prefix: Optional[str] = None) -> None:
        """Clear cache, optionally by prefix."""
        if not self.enabled:
            return
        
        if prefix:
            # Clear by prefix would need pattern matching
            # Not implemented in basic version
            pass
        else:
            await self.memory_cache.clear()
            if self.redis_cache:
                await self.redis_cache.clear()
    
    async def get_or_compute(
        self,
        key_prefix: str,
        compute_func,
        ttl: Optional[int] = None,
        **params
    ) -> Any:
        """Get from cache or compute and cache result."""
        if not self.enabled:
            return await compute_func(**params)
        
        # Generate cache key
        cache_key = self._cache_key(key_prefix, **params)
        
        # Try to get from cache
        result = await self.get(cache_key)
        if result is not None:
            return result
        
        # Compute result
        result = await compute_func(**params)
        
        # Cache result
        await self.set(cache_key, result, ttl=ttl)
        
        return result