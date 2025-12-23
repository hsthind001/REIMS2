"""
Performance Optimization Service

Centralized service for monitoring and optimizing system performance.
Tracks key metrics and provides recommendations for optimization.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import logging
import time

logger = logging.getLogger(__name__)


class PerformanceOptimizationService:
    """
    Performance Optimization Service
    
    Monitors and optimizes:
    - Database query performance
    - API response times
    - Frontend bundle sizes
    - Cache hit rates
    - Memory usage
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_performance_metrics(self) -> Dict:
        """
        Get comprehensive performance metrics.
        
        Returns:
            dict: Performance metrics including:
                - Database query times
                - API response times
                - Cache statistics
                - Memory usage
                - Frontend bundle sizes
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": self._get_database_metrics(),
            "cache": self._get_cache_metrics(),
            "recommendations": self._generate_recommendations()
        }
        
        return metrics
    
    def _get_database_metrics(self) -> Dict:
        """Get database performance metrics."""
        try:
            # Check for slow queries
            slow_queries = self.db.execute(text("""
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    max_time
                FROM pg_stat_statements
                WHERE mean_time > 100  -- Queries taking > 100ms on average
                ORDER BY mean_time DESC
                LIMIT 10
            """)).fetchall()
            
            # Get index usage statistics
            index_stats = self.db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0  -- Unused indexes
                ORDER BY schemaname, tablename
                LIMIT 20
            """)).fetchall()
            
            return {
                "slow_queries": [
                    {
                        "query": row[0][:100] if row[0] else "N/A",
                        "calls": row[1],
                        "mean_time_ms": round(row[3], 2) if row[3] else 0,
                        "max_time_ms": round(row[4], 2) if row[4] else 0
                    }
                    for row in slow_queries
                ],
                "unused_indexes": [
                    {
                        "schema": row[0],
                        "table": row[1],
                        "index": row[2]
                    }
                    for row in index_stats
                ]
            }
        except Exception as e:
            logger.warning(f"Could not fetch database metrics: {e}")
            return {"error": str(e)}
    
    def _get_cache_metrics(self) -> Dict:
        """Get cache performance metrics."""
        try:
            import redis
            from app.core.config import settings
            
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            
            info = redis_client.info()
            
            return {
                "hit_rate": self._calculate_cache_hit_rate(redis_client),
                "memory_used_mb": round(info.get('used_memory', 0) / 1024 / 1024, 2),
                "keys": redis_client.dbsize(),
                "evictions": info.get('evicted_keys', 0)
            }
        except Exception as e:
            logger.warning(f"Could not fetch cache metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_cache_hit_rate(self, redis_client) -> float:
        """Calculate cache hit rate from Redis stats."""
        try:
            info = redis_client.info('stats')
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            
            if hits + misses == 0:
                return 0.0
            
            return round(hits / (hits + misses) * 100, 2)
        except Exception:
            return 0.0
    
    def _generate_recommendations(self) -> List[Dict]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Database recommendations
        db_metrics = self._get_database_metrics()
        if db_metrics.get("slow_queries"):
            recommendations.append({
                "type": "database",
                "priority": "high",
                "message": f"Found {len(db_metrics['slow_queries'])} slow queries. Consider adding indexes or optimizing queries.",
                "action": "Review slow queries and add appropriate indexes"
            })
        
        if db_metrics.get("unused_indexes"):
            recommendations.append({
                "type": "database",
                "priority": "medium",
                "message": f"Found {len(db_metrics['unused_indexes'])} unused indexes. Consider removing to improve write performance.",
                "action": "Review and remove unused indexes"
            })
        
        # Cache recommendations
        cache_metrics = self._get_cache_metrics()
        if cache_metrics.get("hit_rate", 0) < 80:
            recommendations.append({
                "type": "cache",
                "priority": "medium",
                "message": f"Cache hit rate is {cache_metrics.get('hit_rate', 0)}%. Consider increasing cache TTL or expanding cache coverage.",
                "action": "Review cache strategies and TTL settings"
            })
        
        return recommendations
    
    def optimize_database_queries(self, query_pattern: str) -> Dict:
        """
        Analyze and suggest optimizations for a specific query pattern.
        
        Args:
            query_pattern: SQL query pattern to analyze
            
        Returns:
            dict: Optimization suggestions
        """
        suggestions = {
            "index_recommendations": [],
            "query_optimizations": [],
            "estimated_improvement": "N/A"
        }
        
        # Analyze query for missing indexes
        # This is a simplified version - in production, use EXPLAIN ANALYZE
        if "WHERE" in query_pattern.upper():
            # Suggest indexes for WHERE clauses
            suggestions["index_recommendations"].append(
                "Consider adding indexes on columns used in WHERE clauses"
            )
        
        if "JOIN" in query_pattern.upper():
            suggestions["index_recommendations"].append(
                "Ensure foreign key columns have indexes for JOIN operations"
            )
        
        return suggestions

