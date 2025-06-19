"""
EEG Signal Processing Package.

This package provides signal processing capabilities for EEG and biosignal
data using BrainFlow's DataFilter and MLModel libraries. It implements advanced filtering,
denoising, feature extraction, and analysis techniques with robust error handling and
performance optimization.

Core Processor:

- SignalProcessor: Advanced signal processing engine with filtering capabilities
  * Multiple filter types: Butterworth, Chebyshev Type 1, Bessel with zero-phase variants
  * Intelligent filter stability monitoring with automatic parameter adjustment for problematic data
  * Enhanced error handling for synthetic board data and edge cases with graceful degradation
  * Advanced bandpass, bandstop, lowpass, and highpass filtering with configurable parameters
  * Environmental noise removal (50Hz/60Hz) with adaptive frequency detection
  * Wavelet-based denoising using multiple wavelet types (Daubechies, Biorthogonal, Coiflets, etc.)

Key Signal Processing Features:

Advanced Filtering Capabilities:
- Multi-type filtering: Butterworth (stable), Chebyshev Type 1 (sharp rolloff), Bessel (linear phase)
- Intelligent stability analysis with automatic parameter adjustment for Chebyshev filters
- Enhanced validation for synthetic board data with automatic fallback to stable configurations
- Frequency validation based on sampling rate and Nyquist limits with conservative safety margins
- Channel-specific processing with individual error handling and data quality validation
- Real-time filter application with immediate effect monitoring and performance optimization

Wavelet Processing:
- Wavelet transform support with 15+ wavelet types and configurable decomposition levels
- Forward and inverse wavelet transforms with proper coefficient management and metadata preservation
- Optional wavelet denoising with SURE shrinkage, hard/soft thresholding, and noise estimation
- Coefficient-based signal reconstruction with graceful handling of dimension mismatches
- Memory-efficient operations with automatic padding and truncation for coefficient arrays

Independent Component Analysis:
- ICA computation using FastICA algorithm with configurable component numbers (1-16)
- Proper matrix decomposition returning W (unmixing), K (prewhitening), A (mixing), S (sources)
- Error handling for insufficient data or rank-deficient matrices
- Support for multi-channel data with automatic reshaping and dimension validation

Signal Quality Assessment:
- Railed percentage calculation for amplifier saturation detection with configurable gain settings
- Quality scoring system (0-1 scale) with automatic thresholding and status classification
- Multi-channel quality assessment with batch processing and efficiency optimization
- Real-time quality monitoring for continuous data streams and performance tracking

EEG-Specific Analysis:
- Band power calculation for standard EEG frequency bands (Delta, Theta, Alpha, Beta, Gamma)
- Power Spectral Density computation with configurable windowing (Hanning, Hamming, Blackman)
- EEG metrics calculation including mindfulness, restfulness, concentration, and relaxation scores
- ML-based feature extraction using BrainFlow's trained models for cognitive state assessment

Advanced Processing Features:

Data Preprocessing and Conditioning:
- Intelligent detrending with linear and constant detrending operations
- Downsampling with multiple aggregation methods (mean, median, each) and performance optimization
- Peak detection using z-score algorithm with configurable thresholds and influence parameters
- Automatic data validation and cleaning with NaN/Inf detection and replacement

Error Handling:
- Input validation with automatic data type conversion and range checking
- Degradation for synthetic board data with parameter adjustment
- Channel-specific error isolation preventing single channel failures from affecting others
- Automatic recovery mechanisms with logging and user-friendly error reporting

Performance Optimization:
- Memory-efficient operations with in-place processing where possible and automatic cleanup
- Optimized parameter validation reducing computational overhead during real-time processing
- Intelligent caching and coefficient reuse for repeated operations and batch processing
- Thread-safe operations supporting concurrent processing and multi-threaded applications

Accuracy and Validation:
- Parameter validation based on signal processing theory and empirical stability analysis
- Conservative frequency limits ensuring filter stability across different data characteristics
- Proper windowing and overlap handling for spectral analysis and frequency domain operations
- Band power calculations

Technical Implementation:

BrainFlow Integration:
- Full utilization of BrainFlow's DataFilter library for high-performance signal processing
- ML model integration for cognitive state assessment using pre-trained neural networks
- Proper resource management with automatic model preparation and release procedures
- Cross-platform compatibility supporting Windows, Linux, and macOS environments

Algorithm Implementation:
- FastICA algorithm for independent component analysis with proper convergence criteria
- Welch's method for power spectral density estimation with configurable overlap and windowing
- Wavelet transform using lifting scheme implementation for computational efficiency
- Z-score based peak detection with adaptive thresholding and noise robustness

Checks and Balances:
- Parameter validation preventing invalid configurations and numerical instabilities
- Automatic data quality assessment with real-time feedback and optimization suggestions
- Lgging system enabling debugging and performance analysis
- Input sanitization and output validation ensuring data integrity throughout processing pipeline

Use Cases and Applications:
- Real-time EEG monitoring with immediate filter application and quality assessment
- Research applications requiring precise frequency analysis and component separation
- Clinical applications with robust error handling and quality validation requirements
- Educational tools demonstrating signal processing concepts with interactive parameter adjustment
- Brain-computer interface development with low-latency processing and reliable feature extraction

The signal processor provides a solution for
EEG and biosignal analysis, enabling researchers and practitioners to apply advanced
signal processing techniques across diverse data characteristics and hardware configurations.
"""

from .signal_processor import SignalProcessor

__all__ = ["SignalProcessor"]
