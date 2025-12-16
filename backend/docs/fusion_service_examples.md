# Fusion Service Usage Examples

## Overview

This document provides comprehensive examples for using the FusionService to combine semantic and keyword search results using Reciprocal Rank Fusion (RRF).

## Basic Fusion

### Example 1: Simple Fusion

```python
from app.services.fusion_service import FusionService

# Initialize fusion service
fusion_service = FusionService(alpha=0.7, k=60)

# Semantic search results
semantic_results = [
    {'chunk_id': 1, 'similarity': 0.95, 'chunk_text': 'DSCR is 1.20, below threshold'},
    {'chunk_id': 2, 'similarity': 0.85, 'chunk_text': 'Debt service coverage analysis'},
    {'chunk_id': 3, 'similarity': 0.75, 'chunk_text': 'Financial metrics discussion'},
]

# Keyword search results
keyword_results = [
    {'chunk_id': 1, 'score': 2.8, 'chunk_text': 'DSCR is 1.20, below threshold'},
    {'chunk_id': 4, 'score': 2.5, 'chunk_text': 'DSCR calculation shows 1.15'},
    {'chunk_id': 2, 'score': 2.0, 'chunk_text': 'Debt service coverage analysis'},
]

# Fuse results
fused_results = fusion_service.fuse(
    semantic_results=semantic_results,
    keyword_results=keyword_results,
    top_k=10
)

# Display results
for i, result in enumerate(fused_results, 1):
    print(f"{i}. Chunk {result['chunk_id']}")
    print(f"   Fused Score: {result['fused_score']:.6f}")
    print(f"   Semantic Rank: {result['semantic_rank']}, Keyword Rank: {result['keyword_rank']}")
    print(f"   Text: {result['chunk_text'][:100]}...")
    print()
```

### Example 2: Fusion with Score Logging

```python
# Enable score logging for debugging
fused_results = fusion_service.fuse(
    semantic_results=semantic_results,
    keyword_results=keyword_results,
    top_k=10,
    log_scores=True  # Logs detailed fusion scores
)
```

## Parameter Tuning

### Example 3: Tune Alpha for Optimal Performance

```python
from app.services.fusion_service import FusionService

fusion_service = FusionService(alpha=0.7, k=60)

# Your search results
semantic_results = [...]  # From semantic search
keyword_results = [...]   # From keyword search
ground_truth = [1, 3, 5, 7]  # Known relevant chunk IDs

# Tune alpha
tuning_result = fusion_service.tune_alpha(
    semantic_results=semantic_results,
    keyword_results=keyword_results,
    ground_truth=ground_truth,
    alpha_range=(0.0, 1.0),
    alpha_step=0.1
)

print(f"Best alpha: {tuning_result['best_alpha']}")
print(f"Best precision: {tuning_result['best_score']:.4f}")

# Use best alpha
optimal_service = FusionService(alpha=tuning_result['best_alpha'], k=60)
fused = optimal_service.fuse(semantic_results, keyword_results, top_k=10)
```

### Example 4: Tune K Parameter

```python
# Tune k parameter
tuning_result = fusion_service.tune_k(
    semantic_results=semantic_results,
    keyword_results=keyword_results,
    ground_truth=ground_truth,
    k_range=(30, 100),
    k_step=10
)

print(f"Best k: {tuning_result['best_k']}")
print(f"Best precision: {tuning_result['best_score']:.4f}")
```

## Evaluation

### Example 5: Evaluate Fusion Performance

```python
from app.services.fusion_service import FusionService
from app.services.fusion_evaluation import FusionEvaluation

# Fuse results
fusion_service = FusionService(alpha=0.7, k=60)
fused_results = fusion_service.fuse(semantic_results, keyword_results, top_k=20)

# Evaluate
evaluator = FusionEvaluation(top_k=20)
metrics = evaluator.evaluate(
    fused_results=fused_results,
    ground_truth=[1, 3, 5, 7, 9]  # Relevant chunk IDs
)

print("Evaluation Metrics:")
print(f"  Precision@20: {metrics['precision_at_k']:.4f}")
print(f"  Recall@20: {metrics['recall_at_k']:.4f}")
print(f"  F1@20: {metrics['f1_at_k']:.4f}")
print(f"  NDCG: {metrics['ndcg']:.4f}")
print(f"  MRR: {metrics['mrr']:.4f}")
print(f"  Relevant Retrieved: {metrics['relevant_retrieved']}/{metrics['total_relevant']}")
```

### Example 6: Compare Different Alpha Values

```python
import matplotlib.pyplot as plt

alpha_values = []
precision_scores = []

for alpha in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
    service = FusionService(alpha=alpha, k=60)
    fused = service.fuse(semantic_results, keyword_results, top_k=20)
    
    evaluator = FusionEvaluation(top_k=20)
    metrics = evaluator.evaluate(fused, ground_truth)
    
    alpha_values.append(alpha)
    precision_scores.append(metrics['precision_at_k'])

# Plot results
plt.plot(alpha_values, precision_scores, marker='o')
plt.xlabel('Alpha')
plt.ylabel('Precision@20')
plt.title('Fusion Performance vs Alpha')
plt.grid(True)
plt.show()
```

## Integration with RAGRetrievalService

### Example 7: RRF Fusion via RAG Service

```python
from app.services.rag_retrieval_service import RAGRetrievalService
from app.db.database import SessionLocal

db = SessionLocal()
rag_service = RAGRetrievalService(db)

# RRF fusion search
results = rag_service.retrieve_relevant_chunks(
    query="DSCR below 1.25",
    top_k=10,
    use_rrf=True,  # Enable RRF fusion
    rrf_alpha=0.7,  # 70% semantic, 30% keyword
    rrf_k=60,      # RRF constant
    property_id=1
)

for result in results:
    print(f"Fused Score: {result['rrf_score']}")
    print(f"Semantic Rank: {result['semantic_rank']}")
    print(f"Keyword Rank: {result['keyword_rank']}")
```

## Advanced Usage

### Example 8: Custom Fusion Formula Components

```python
# Calculate individual components
fused_score, semantic_comp, keyword_comp = fusion_service.calculate_fused_score(
    semantic_rank=1,
    keyword_rank=2
)

print(f"Fused Score: {fused_score:.6f}")
print(f"  Semantic Component: {semantic_comp:.6f}")
print(f"  Keyword Component: {keyword_comp:.6f}")
```

### Example 9: Batch Evaluation Across Multiple Queries

```python
from app.services.fusion_evaluation import FusionEvaluation

evaluator = FusionEvaluation(top_k=20)

# Multiple queries
query_results = [
    fused_results_1,
    fused_results_2,
    fused_results_3,
]

ground_truths = [
    [1, 3, 5],  # Ground truth for query 1
    [2, 4, 6],  # Ground truth for query 2
    [1, 2, 7],  # Ground truth for query 3
]

# Evaluate all queries
avg_metrics = evaluator.evaluate_multiple_queries(query_results, ground_truths)

print("Average Metrics Across Queries:")
for metric, value in avg_metrics.items():
    if isinstance(value, float):
        print(f"  {metric}: {value:.4f}")
```

## Configuration

### Example 10: Using Configuration File

```python
from app.config.fusion_config import fusion_config

# Get default configuration
config = fusion_config.get_config_dict()
print(f"Default alpha: {config['alpha']}")
print(f"Default k: {config['k']}")

# Create service with config defaults
fusion_service = FusionService(
    alpha=fusion_config.ALPHA,
    k=fusion_config.K
)
```

### Example 11: Environment Variable Configuration

```bash
# Set fusion parameters via environment variables
export FUSION_ALPHA=0.8
export FUSION_K=50
export FUSION_LOG_SCORES=true

# Then use in code
from app.config.fusion_config import fusion_config
fusion_service = FusionService(
    alpha=fusion_config.ALPHA,
    k=fusion_config.K
)
```

## Best Practices

1. **Start with Defaults**: Use alpha=0.7, k=60 initially
2. **Tune Based on Data**: Use tuning scripts with your actual queries
3. **Evaluate Regularly**: Monitor precision/recall metrics
4. **Log Scores**: Enable logging during development for debugging
5. **Preserve Metadata**: Fusion automatically preserves all metadata
6. **Handle Missing Results**: RRF gracefully handles chunks in only one result set

## Troubleshooting

### Low Precision

- Try different alpha values (tune_alpha)
- Adjust k parameter (tune_k)
- Check ground truth quality
- Verify both search methods are working

### Unexpected Rankings

- Check semantic_component and keyword_component values
- Verify ranks are correct (1-indexed)
- Enable score logging for debugging
- Compare with individual search results

