# Appendix: Research References & Sources

This document contains all research sources referenced in the implementation plan.

---

## Time Series Anomaly Detection (2025)

### Primary Libraries

1. **PyOD 2.0: Python Outlier Detection Library**
   - Paper: [PyOD 2: A Python Library for Outlier Detection with LLM-powered Model Selection](https://dl.acm.org/doi/10.1145/3701716.3715196)
   - arXiv: [PyOD 2 arXiv Paper](https://arxiv.org/abs/2412.12154)
   - GitHub: [yzhao062/pyod](https://github.com/yzhao062/pyod)
   - Features: 45+ algorithms, LLM-powered selection, PyTorch integration
   - Release: Late 2024/Early 2025
   - Downloads: 26+ million

2. **dtaianomaly: Time Series Anomaly Detection Library**
   - arXiv: [dtaianomaly Paper](https://arxiv.org/abs/2502.14381)
   - Features: scikit-learn API, preprocessing, confidence prediction
   - Release: 2025
   - Purpose-built for time series data

3. **Anomaly Detection Resources**
   - Repository: [GitHub - yzhao062/anomaly-detection-resources](https://github.com/yzhao062/anomaly-detection-resources)
   - Updated: Late 2025 for LLM and VLM works
   - Comprehensive collection of books, papers, videos, toolboxes

### Implementation Guides

4. **Anomaly Detection in Time Series - PyCharm Blog**
   - Link: [PyCharm Blog](https://blog.jetbrains.com/pycharm/2025/01/anomaly-detection-in-time-series/)
   - Date: January 2025
   - Coverage: Practical toolkit for time series anomaly detection

5. **GitHub - rob-med/awesome-TS-anomaly-detection**
   - Link: [awesome-TS-anomaly-detection](https://github.com/rob-med/awesome-TS-anomaly-detection)
   - Content: List of tools & datasets for time series anomaly detection

6. **ADTK (Anomaly Detection Toolkit)**
   - Docs: [ADTK Documentation](https://adtk.readthedocs.io/en/stable/)
   - Features: Unsupervised/rule-based time series detection
   - API: Unified for detectors, transformers, aggregators

---

## Explainable AI (XAI) - SHAP & LIME (2025)

### SHAP (SHapley Additive exPlanations)

1. **Explainable AI (XAI) 2025: SHAP, LIME & Model Interpretability**
   - Link: [TensorBlue Blog](https://tensorblue.com/blog/explainable-ai-xai-shap-lime-model-interpretability-2025)
   - Date: 2025
   - Coverage: Complete guide to SHAP and LIME

2. **Explainable AI for Intrusion Detection Systems**
   - Link: [IEEE Xplore](https://ieeexplore.ieee.org/document/10440604/)
   - Paper: LIME and SHAP Applicability on Multi-Layer Perceptron
   - Findings: SHAP more accurate but 1.8x slower than LIME

### Comparative Studies

3. **Explainable AI for Forensic Analysis: SHAP and LIME**
   - Link: [MDPI Applied Sciences](https://www.mdpi.com/2076-3417/15/13/7329)
   - Date: 2025
   - Models: XGBoost and TabNet with UNSW-NB15 dataset

4. **Evaluating ML-based Intrusion Detection with Explainable AI**
   - Link: [Frontiers in Computer Science](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1520741/full)
   - Date: 2025
   - Tools: SHAP, LIME, and ELI5 for transparency

5. **Systematic Review: XAI in Intrusion Detection Systems**
   - Link: [Frontiers in AI](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1526221/full)
   - Date: 2025
   - Focus: Enhancing transparency and interpretability

### Performance Benchmarks

**Key Findings from Research**:
- SHAP computation: ~1.8x slower than LIME per sample
- SHAP provides more stable global feature rankings
- LIME useful for rapid local inspection of anomalies
- SHAP better for accuracy, LIME better for speed
- Recommended: Use both (SHAP for background, LIME for on-demand)

---

## Active Learning for Anomaly Detection (2025)

### Frameworks

1. **ALADAEN: Ranking-enhanced Anomaly Detection**
   - Link: [Nature Scientific Reports](https://www.nature.com/articles/s41598-025-25621-0)
   - Date: January 2025
   - Features: Dual adversarial AutoEncoders with ranking-oriented active learning
   - Innovation: Prioritizes most informative anomalies for analyst feedback

2. **ALFred: Active Learning Framework for Real-world Anomaly Detection**
   - arXiv: [ALFred Paper](https://arxiv.org/html/2508.09058)
   - HTML: [ALFred HTML](https://arxiv.org/html/2508.09058v1)
   - Date: August 2025
   - Features: Human-in-the-loop, dynamic threshold adaptation
   - Innovation: Adaptive thresholds based on historical labeled context

3. **ALIF: Active Learning-based Isolation Forest**
   - Link: [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0020025524009265)
   - Date: 2025
   - Features: Expert feedback integration with Isolation Forest
   - Innovation: Enhancing anomaly detection through expert feedback

### Industrial Applications

4. **ALMAN: Data-efficient Active Learning for Manufacturing**
   - Link: [Springer](https://link.springer.com/article/10.1007/s10696-024-09588-0)
   - Date: February 2025
   - Focus: Time series data in industrial CPS
   - Innovation: Minimizes expert burden while improving performance

5. **Active Learning for Computational Workflows**
   - Link: [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0167739X24005727)
   - arXiv: [Arxiv HTML](https://arxiv.org/html/2405.06133v1)
   - Date: December 2024/2025
   - Features: Incremental training with confidence-driven feedback loop

6. **Active Learning for Mobile Communications**
   - Link: [MDPI Sensors](https://www.mdpi.com/1424-8220/23/1/126)
   - Date: 2023 (still relevant)
   - Features: Expert-assisted anomaly detection methodology

### Key Mechanisms

**Feedback Loop Pattern**:
1. Oracle (human expert) labels uncertain data points
2. System creates new subset of normal labeled data
3. Unsupervised model trained incrementally
4. Confidence levels drive next round of queries

**Dynamic Threshold Adaptation** (from ALFred):
- Adjusts detection boundaries based on historical context
- Uses feedback to refine context-specific anomalies
- Reduces false positives over time

---

## Document Layout Understanding - LayoutLM (2020-2025)

### Primary Papers

1. **LayoutLM: Pre-training of Text and Layout**
   - arXiv: [LayoutLM Paper](https://arxiv.org/pdf/1912.13318)
   - ACM: [ACM Publication](https://dl.acm.org/doi/abs/10.1145/3394486.3403172)
   - Date: 2020 (foundational paper)
   - Innovation: Combines text with visual layout information

2. **Your Ultimate Guide to Understanding LayoutLM**
   - Link: [Nanonets Blog](https://nanonets.com/blog/layoutlm-explained/)
   - Coverage: Comprehensive tutorial and implementation guide
   - Includes: v1, v2, v3 explanations

### Implementation Guides

3. **Microsoft Document Intelligence - Layout Analysis**
   - Link: [Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/layout?view=doc-intel-4.0.0)
   - Date: 2025
   - Features: Prebuilt layout model documentation

4. **LayoutLM Hugging Face Documentation**
   - Link: [Hugging Face Docs](https://huggingface.co/docs/transformers/model_doc/layoutlm)
   - Implementation: Transformers library integration

5. **Papers Explained: Layout LM**
   - Link: [Medium - DAIR.AI](https://medium.com/dair-ai/papers-explained-10-layout-lm-32ec4bad6406)
   - Author: Ritvik Rastogi
   - Coverage: Detailed explanation of architecture and use cases

### Technical Details

**Coordinate System**:
- Bounding box format: (x0, y0, x1, y1)
- Normalization: Scaled to 0-1000 range (virtual coordinate system)
- Purpose: Consistent processing across different document sizes

**Processing Pipeline**:
1. OCR (Tesseract/EasyOCR) extracts text + coordinates
2. Normalize coordinates to 0-1000 scale
3. LayoutLM processes layout + text semantics
4. Predict entity types and locations

**Evolution**:
- **LayoutLMv1** (2020): Text + 2D position embeddings
- **LayoutLMv2** (2021): Added visual embeddings
- **LayoutLMv3** (2022): Unified text-image multimodal pre-training
- **2025**: More powerful and universal AI models built on foundation

---

## Implementation Patterns & Best Practices

### Anomaly Detection Strategies

1. **Ensemble Methods**
   - Combine multiple algorithms (vote-based)
   - Weight by confidence scores
   - Minimum agreement threshold (e.g., 2 methods)

2. **Multi-Window Detection**
   - Short-term: 3 months
   - Medium-term: 12 months
   - Long-term: 24 months
   - Consensus: Detected in multiple windows

3. **Adaptive Thresholds**
   - Baseline: Global threshold (e.g., 2σ, 15% change)
   - Adjust: Per-account volatility multipliers
   - Learn: From user feedback (precision-recall optimization)

### Active Learning Strategies

**Uncertainty Sampling**:
- Low confidence predictions
- Near decision boundary
- Conflicting model outputs
- Novel patterns (far from training data)

**Query Strategies**:
- Margin sampling: Points closest to decision boundary
- Entropy-based: Maximum uncertainty
- Committee-based: Disagreement among ensemble

**Stopping Criteria**:
- Confidence threshold reached
- Budget exhausted (max queries)
- Performance plateau

### XAI Best Practices

**When to Use SHAP**:
- Model validation and debugging
- Feature importance analysis
- Regulatory compliance (need justification)
- Background jobs (not time-sensitive)

**When to Use LIME**:
- On-demand user queries
- Real-time explanations
- Interactive dashboards
- Quick anomaly inspection

**Explanation Quality**:
- Combine technical + natural language
- Provide multiple levels of detail
- Include uncertainty estimates
- Suggest actionable next steps

---

## Tools & Libraries Matrix

| Category | Tool | Version | Purpose | Source |
|----------|------|---------|---------|--------|
| Anomaly Detection | PyOD | 2.0.0 | 45+ algorithms | [GitHub](https://github.com/yzhao062/pyod) |
| Time Series | dtaianomaly | 1.0.0 | TS-specific detection | [arXiv](https://arxiv.org/abs/2502.14381) |
| Explainability | SHAP | 0.44.0 | Global feature importance | [GitHub](https://github.com/slundberg/shap) |
| Explainability | LIME | 0.2.0.1 | Local explanations | [GitHub](https://github.com/marcotcr/lime) |
| Layout Understanding | LayoutLM | v3 | Document understanding | [Hugging Face](https://huggingface.co/microsoft/layoutlmv3-base) |
| PDF Processing | PDFPlumber | Latest | Word-level coordinates | [GitHub](https://github.com/jsvine/pdfplumber) |
| Forecasting | Prophet | Latest | Time series forecasting | [Facebook](https://facebook.github.io/prophet/) |
| Model Selection | llama-index | 0.9.48 | LLM-powered selection | [GitHub](https://github.com/run-llama/llama_index) |

---

## Academic Citations (BibTeX)

```bibtex
@inproceedings{zhao2025pyod2,
  title={PyOD 2: A Python Library for Outlier Detection with LLM-powered Model Selection},
  author={Zhao, Yue and others},
  booktitle={Companion Proceedings of the ACM on Web Conference 2025},
  year={2025},
  doi={10.1145/3701716.3715196}
}

@article{dtaianomaly2025,
  title={dtaianomaly: A Python library for time series anomaly detection},
  author={Authors},
  journal={arXiv preprint arXiv:2502.14381},
  year={2025}
}

@article{aladaen2025,
  title={Ranking-enhanced anomaly detection using Active Learning-assisted Attention Adversarial Dual AutoEncoder},
  author={Authors},
  journal={Scientific Reports},
  volume={15},
  year={2025},
  doi={10.1038/s41598-025-25621-0}
}

@article{alfred2025,
  title={ALFred: An Active Learning Framework for Real-world Semi-supervised Anomaly Detection with Adaptive Thresholds},
  author={Authors},
  journal={arXiv preprint arXiv:2508.09058},
  year={2025}
}

@inproceedings{layoutlm2020,
  title={LayoutLM: Pre-training of Text and Layout for Document Image Understanding},
  author={Xu, Yiheng and Li, Minghao and Cui, Lei and Huang, Shaohan and Wei, Furu and Zhou, Ming},
  booktitle={Proceedings of the 26th ACM SIGKDD International Conference on Knowledge Discovery \& Data Mining},
  pages={1192--1200},
  year={2020},
  doi={10.1145/3394486.3403172}
}
```

---

## Additional Resources

### Tutorials & Guides

1. **Time Series Anomaly Detection in Python - Turing**
   - Link: [Turing KB](https://www.turing.com/kb/time-series-anomaly-detection-in-python)
   - Practical implementation guide

2. **Anomaly Detection for Time Series - Spot Intelligence**
   - Link: [Spot Intelligence](https://spotintelligence.com/2023/03/18/anomaly-detection-for-time-series/)
   - Top 8 algorithms and libraries

3. **Anomaly Detection in Time Series - Neptune.ai**
   - Link: [Neptune.ai Blog](https://neptune.ai/blog/anomaly-detection-in-time-series)
   - Comprehensive overview

### Datasets for Testing

1. **UNSW-NB15 Dataset** - Network intrusion detection
2. **Yahoo Anomaly Dataset** - Time series anomalies
3. **Numenta Anomaly Benchmark (NAB)** - Real-world time series
4. **ODDS Library** - Outlier detection datasets

### Community & Forums

1. **PyOD Discussions** - [GitHub Discussions](https://github.com/yzhao062/pyod/discussions)
2. **SHAP Issues** - [GitHub Issues](https://github.com/slundberg/shap/issues)
3. **Hugging Face Forums** - [LayoutLM](https://discuss.huggingface.co/)

---

## Version History

- **v1.0** (2025-12-21): Initial compilation of research sources
- Updated: As of December 2025

---

**Note**: All links verified as of December 2025. Some papers may require institutional access.
