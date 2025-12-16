"""
Benchmark script for RAG Retrieval Service optimizations.

Usage:
    python -m pytest backend/tests/benchmark_rag_retrieval.py -v --benchmark-only
    
Or run directly:
    python backend/tests/benchmark_rag_retrieval.py
"""
import time
import statistics
import tracemalloc
from typing import List, Dict
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.services.rag_retrieval_service import RAGRetrievalService
from app.services.rag_retrieval_service_optimized_v2 import OptimizedRAGRetrievalService
from app.services.embedding_service import EmbeddingService


class BenchmarkResults:
    """Store benchmark results."""
    
    def __init__(self, name: str):
        self.name = name
        self.latencies = []
        self.memory_usage = []
        self.query_counts = []
        self.cache_hits = 0
        self.cache_misses = 0
    
    def add_result(self, latency: float, memory_mb: float, queries: int = 0):
        self.latencies.append(latency)
        self.memory_usage.append(memory_mb)
        if queries > 0:
            self.query_counts.append(queries)
    
    def get_stats(self) -> Dict:
        return {
            'name': self.name,
            'count': len(self.latencies),
            'latency_mean': statistics.mean(self.latencies) if self.latencies else 0,
            'latency_p50': statistics.median(self.latencies) if self.latencies else 0,
            'latency_p95': self._percentile(self.latencies, 95) if self.latencies else 0,
            'latency_p99': self._percentile(self.latencies, 99) if self.latencies else 0,
            'memory_mean_mb': statistics.mean(self.memory_usage) if self.memory_usage else 0,
            'memory_max_mb': max(self.memory_usage) if self.memory_usage else 0,
            'queries_mean': statistics.mean(self.query_counts) if self.query_counts else 0,
            'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) * 100 if (self.cache_hits + self.cache_misses) > 0 else 0
        }
    
    @staticmethod
    def _percentile(data: List[float], p: int) -> float:
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


def benchmark_retrieval(
    service,
    queries: List[str],
    iterations: int = 10,
    top_k: int = 10
) -> BenchmarkResults:
    """Benchmark retrieval service."""
    results = BenchmarkResults(service.__class__.__name__)
    
    for iteration in range(iterations):
        for query in queries:
            # Start memory tracking
            tracemalloc.start()
            start_time = time.time()
            
            # Execute retrieval
            try:
                chunks = service.retrieve_relevant_chunks(
                    query=query,
                    top_k=top_k,
                    use_rrf=True
                )
                
                # Measure
                elapsed = time.time() - start_time
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                memory_mb = peak / 1024 / 1024
                
                results.add_result(elapsed, memory_mb)
                
            except Exception as e:
                print(f"Error in iteration {iteration}, query '{query}': {e}")
                tracemalloc.stop()
    
    return results


def compare_services():
    """Compare original vs optimized service."""
    db: Session = SessionLocal()
    
    try:
        embedding_service = EmbeddingService(db)
        
        # Initialize services
        original_service = RAGRetrievalService(db, embedding_service)
        optimized_service = OptimizedRAGRetrievalService(db, embedding_service)
        
        # Test queries
        test_queries = [
            "What was NOI for Eastern Shore in Q3 2024?",
            "Show me properties with losses",
            "What is the DSCR for all properties?",
            "Compare revenue across properties",
            "What was the cash flow for Q2?",
            "Show me rent roll data",
            "What are the operating expenses?",
            "Find properties with high vacancy rates"
        ]
        
        print("=" * 80)
        print("RAG Retrieval Service Benchmark")
        print("=" * 80)
        print(f"Test queries: {len(test_queries)}")
        print(f"Iterations per query: 5")
        print(f"Total runs: {len(test_queries) * 5}")
        print()
        
        # Benchmark original
        print("Benchmarking ORIGINAL service...")
        original_results = benchmark_retrieval(
            original_service,
            test_queries,
            iterations=5,
            top_k=10
        )
        
        # Benchmark optimized
        print("Benchmarking OPTIMIZED service...")
        optimized_results = benchmark_retrieval(
            optimized_service,
            test_queries,
            iterations=5,
            top_k=10
        )
        
        # Print results
        print()
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        
        orig_stats = original_results.get_stats()
        opt_stats = optimized_results.get_stats()
        
        print(f"\n{'Metric':<30} {'Original':<20} {'Optimized':<20} {'Improvement':<20}")
        print("-" * 90)
        
        # Latency
        latency_improvement = (1 - opt_stats['latency_p95'] / orig_stats['latency_p95']) * 100
        print(f"{'Latency p95 (s)':<30} {orig_stats['latency_p95']:<20.3f} {opt_stats['latency_p95']:<20.3f} {latency_improvement:>18.1f}%")
        
        latency_mean_improvement = (1 - opt_stats['latency_mean'] / orig_stats['latency_mean']) * 100
        print(f"{'Latency mean (s)':<30} {orig_stats['latency_mean']:<20.3f} {opt_stats['latency_mean']:<20.3f} {latency_mean_improvement:>18.1f}%")
        
        # Memory
        memory_improvement = (1 - opt_stats['memory_max_mb'] / orig_stats['memory_max_mb']) * 100
        print(f"{'Memory max (MB)':<30} {orig_stats['memory_max_mb']:<20.1f} {opt_stats['memory_max_mb']:<20.1f} {memory_improvement:>18.1f}%")
        
        # Cache hit rate
        print(f"{'Cache hit rate (%)':<30} {'N/A':<20} {opt_stats['cache_hit_rate']:<20.1f} {'New feature':>18}")
        
        # Throughput estimate
        orig_throughput = 1 / orig_stats['latency_mean'] if orig_stats['latency_mean'] > 0 else 0
        opt_throughput = 1 / opt_stats['latency_mean'] if opt_stats['latency_mean'] > 0 else 0
        throughput_improvement = (opt_throughput / orig_throughput - 1) * 100 if orig_throughput > 0 else 0
        print(f"{'Throughput (qps)':<30} {orig_throughput:<20.1f} {opt_throughput:<20.1f} {throughput_improvement:>18.1f}%")
        
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ Latency improvement: {latency_improvement:.1f}%")
        print(f"✅ Memory improvement: {memory_improvement:.1f}%")
        print(f"✅ Throughput improvement: {throughput_improvement:.1f}%")
        print(f"✅ Cache hit rate: {opt_stats['cache_hit_rate']:.1f}%")
        
        # Verify targets
        print()
        print("=" * 80)
        print("TARGET VERIFICATION")
        print("=" * 80)
        
        targets_met = []
        if opt_stats['latency_p95'] < 1.0:
            print(f"✅ Latency p95 target met: {opt_stats['latency_p95']:.3f}s < 1.0s")
            targets_met.append(True)
        else:
            print(f"❌ Latency p95 target NOT met: {opt_stats['latency_p95']:.3f}s >= 1.0s")
            targets_met.append(False)
        
        if opt_throughput >= 50:
            print(f"✅ Throughput target met: {opt_throughput:.1f} qps >= 50 qps")
            targets_met.append(True)
        else:
            print(f"❌ Throughput target NOT met: {opt_throughput:.1f} qps < 50 qps")
            targets_met.append(False)
        
        if opt_stats['memory_max_mb'] < 1024:
            print(f"✅ Memory target met: {opt_stats['memory_max_mb']:.1f} MB < 1024 MB")
            targets_met.append(True)
        else:
            print(f"❌ Memory target NOT met: {opt_stats['memory_max_mb']:.1f} MB >= 1024 MB")
            targets_met.append(False)
        
        print()
        if all(targets_met):
            print("🎉 ALL TARGETS MET!")
        else:
            print("⚠️  Some targets not met. Review optimizations.")
        
    finally:
        db.close()


if __name__ == "__main__":
    compare_services()

