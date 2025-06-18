"""
Help system for the EEG Processor application.

This module provides contextual help information about various aspects
of EEG data collection, processing, and visualization.
"""

from typing import Optional

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QWidget,
    QTextBrowser,
    QTabWidget,
)

# Dictionary of help content for different topics
HELP_CONTENT = {
    # Board Connection Section
    "board_selection": {
        "title": "EEG Board Selection",
        "content": """
        <h3>EEG Board Selection</h3>
        <p>This section allows you to select the EEG device to connect to.</p>

        <h4>Common Board Types:</h4>
        <ul>
            <li><b>Synthetic Board</b>: A virtual board that generates simulated EEG data.
            Ideal for testing the application without physical hardware.</li>

            <li><b>Playback File Board</b>: Reads previously recorded EEG data from a file.
            Allows you to analyze pre-recorded sessions.</li>

            <li><b>OpenBCI Boards (Cyton, Ganglion)</b>: Open-source EEG devices with different
            channel counts. Cyton has 8 channels, Cyton+Daisy has 16 channels, Ganglion has 4 channels.</li>

            <li><b>Muse</b>: Consumer EEG headband with 4-5 channels designed for meditation.</li>

            <li><b>g.tec Unicorn</b>: Research-grade EEG headset with 8 channels.</li>
        </ul>

        <p>When selecting a board, the application will automatically show the required
        parameters for connection (serial port, IP address, etc.).</p>
        """,
    },
    "connection_params": {
        "title": "Connection Parameters",
        "content": """
        <h3>Connection Parameters</h3>
        <p>Different EEG boards require different parameters for connection:</p>

        <ul>
            <li><b>Serial Port</b>: The COM port where your EEG device is connected (e.g., COM3, /dev/ttyUSB0).
            Used for boards connecting via serial like OpenBCI.</li>

            <li><b>MAC Address</b>: Bluetooth MAC address for devices that connect via Bluetooth
            (format: XX:XX:XX:XX:XX:XX).</li>

            <li><b>IP Address</b>: Network address for boards connecting via WiFi or network.</li>

            <li><b>IP Port</b>: Network port number for WiFi-connected boards.</li>

            <li><b>File</b>: Path to data file for playback board mode.</li>

            <li><b>Serial Number</b>: Unique identifier for certain boards like g.tec Unicorn.</li>
        </ul>

        <p>Required fields are highlighted. Only fill in the fields needed for your specific board type.</p>
        """,
    },
    "preset_selection": {
        "title": "Data Preset Selection",
        "content": """
        <h3>Data Preset Selection</h3>
        <p>Presets determine which data streams are gathered from the EEG device:</p>

        <ul>
            <li><b>Default Preset</b>: Primary EEG data channels. This is recommended for most EEG analysis.</li>

            <li><b>Auxiliary Preset</b>: Additional sensor data such as accelerometer and gyroscope measurements.
            Useful for motion analysis and artifact detection.</li>

            <li><b>Ancillary Preset</b>: Additional data streams like battery level, peripheral sensors, etc.</li>
        </ul>

        <p>Not all boards support all presets. The application will only allow you to select
        presets that are available for your chosen board.</p>
        """,
    },
    # Streaming Section
    "streaming": {
        "title": "EEG Data Streaming",
        "content": """
        <h3>EEG Data Streaming</h3>
        <p>This section controls the data flow from your EEG device to the application.</p>

        <ul>
            <li><b>Start Stream</b>: Begin receiving data from the connected EEG device.
            This initializes the data buffer and starts the visualization.</li>

            <li><b>Stop Stream</b>: Halt the data stream from the EEG device. This stops
            data collection but maintains the connection to the device.</li>
        </ul>

        <p>While streaming, you can view the data in real-time, record it to a file,
        and apply various processing techniques.</p>

        <p>The buffer size determines how much data is stored in memory. Default is 450,000 samples,
        which is approximately 30 minutes of data at 250Hz sampling rate.</p>
        """,
    },
    # Processing Section
    "bandpass_filter": {
        "title": "Bandpass Filter",
        "content": """
        <h3>Bandpass Filter</h3>
        <p>A bandpass filter allows frequencies within a certain range to pass through and attenuates frequencies outside that range.</p>

        <h4>Parameters:</h4>
        <ul>
            <li><b>Low Cut</b>: The lower frequency boundary (Hz). Signals below this frequency will be attenuated.</li>
            <li><b>High Cut</b>: The upper frequency boundary (Hz). Signals above this frequency will be attenuated.</li>
        </ul>

        <h4>Common EEG Bandpass Settings:</h4>
        <ul>
            <li>General EEG: 1-50 Hz</li>
            <li>Removing slow drifts: 0.5-50 Hz</li>
            <li>Focusing on specific brain rhythms:
                <ul>
                    <li>Delta waves (sleep): 0.5-4 Hz</li>
                    <li>Theta waves (drowsiness/meditation): 4-8 Hz</li>
                    <li>Alpha waves (relaxation): 8-13 Hz</li>
                    <li>Beta waves (alert/working): 13-30 Hz</li>
                    <li>Gamma waves (cognitive processing): 30-100 Hz</li>
                </ul>
            </li>
        </ul>

        <p>Narrower bandpass ranges focus on specific neural oscillations but may filter out
        important information. Wider ranges preserve more data but may include more noise.</p>
        """,
    },
    "notch_filter": {
        "title": "Notch Filter",
        "content": """
        <h3>Notch Filter</h3>
        <p>A notch filter removes a specific frequency band, typically used to eliminate power line interference.</p>

        <h4>Options:</h4>
        <ul>
            <li><b>50 Hz</b>: Use in regions with 50 Hz power systems (Europe, Asia, Africa, most of Australia)</li>
            <li><b>60 Hz</b>: Use in regions with 60 Hz power systems (North America, parts of South America)</li>
        </ul>

        <p>Power line interference appears as a sharp spike in the frequency spectrum at 50 or 60 Hz.
        This filter helps to remove this interference without affecting too much of the surrounding
        frequency content.</p>

        <p>In laboratory environments with proper electrical shielding, this filter might not be necessary.
        However, for most home or office recordings, this filter is highly recommended.</p>
        """,
    },
    "denoising": {
        "title": "Wavelet Denoising",
        "content": """
        <h3>Wavelet Denoising</h3>
        <p>Wavelet denoising uses wavelet transforms to remove noise while preserving signal features.</p>

        <h4>Wavelet Types:</h4>
        <ul>
            <li><b>DB4 (Daubechies 4)</b>: General-purpose wavelet, good for most EEG signals</li>
            <li><b>DB6 (Daubechies 6)</b>: Better frequency resolution than DB4</li>
            <li><b>BIOR3.9 (Biorthogonal 3.9)</b>: Good for detecting transient events in EEG</li>
        </ul>

        <p>Wavelet denoising is particularly effective for removing random noise while preserving
        important signal characteristics. It works by decomposing the signal into different frequency
        components (wavelets), thresholding coefficients to remove noise, and reconstructing the signal.</p>

        <p>This denoising technique is especially useful when standard filtering approaches remove
        too much valuable data or don't effectively target the noise in your recording.</p>
        """,
    },
    "detrend": {
        "title": "Detrending",
        "content": """
        <h3>Detrending</h3>
        <p>Detrending removes slow drifts and trends from the EEG signal that are not related to brain activity.</p>

        <p>Common causes of trends in EEG data include:</p>
        <ul>
            <li>Electrode drift due to skin potential changes</li>
            <li>Sweating (changing impedance over time)</li>
            <li>Slow shifts in the reference electrode potential</li>
            <li>Thermal drift in amplifier circuits</li>
        </ul>

        <p>Detrending is important because these slow trends can mask the more rapid changes in brain activity
        that are of interest. The detrending operation subtracts either a constant baseline (constant detrend)
        or a linear trend (linear detrend) from the signal.</p>

        <p>For EEG data, linear detrending is typically most appropriate as it handles gradual
        shifts in the baseline.</p>
        """,
    },
    # Visualization Section
    "eeg_visualization": {
        "title": "EEG Visualization",
        "content": """
        <h3>EEG Visualization</h3>
        <p>The EEG visualization window displays real-time or recorded EEG data in multiple formats:</p>

        <h4>Components:</h4>
        <ul>
            <li><b>Time Series</b>: Shows the amplitude of EEG signals over time for each channel</li>
            <li><b>Power Spectrum</b>: Displays the frequency content of the signals using Fast Fourier Transform (FFT)</li>
            <li><b>Band Powers</b>: Shows the relative power in different frequency bands (Delta, Theta, Alpha, Beta, Gamma)</li>
        </ul>

        <h4>Interaction:</h4>
        <p>You can interact with the plots in several ways:</p>
        <ul>
            <li><b>Zoom</b>: Use mouse wheel or right-click and drag</li>
            <li><b>Pan</b>: Left-click and drag</li>
            <li><b>Reset View</b>: Double right-click</li>
            <li><b>Data Tooltip</b>: Hover over data points</li>
        </ul>

        <p>The small colored dots at the end of each EEG channel indicate signal quality:
        green for good, yellow for fair, and red for poor quality.</p>
        """,
    },
    "brain_map": {
        "title": "Brain Map Visualization",
        "content": """
        <h3>Brain Map Visualization</h3>
        <p>The brain map displays electrode positions on a 2D representation of the head
        and indicates signal quality or other metrics using color coding.</p>

        <h4>Components:</h4>
        <ul>
            <li><b>Head Outline</b>: 2D circular representation of the head</li>
            <li><b>Electrodes</b>: Dots positioned according to the international 10-20 system</li>
            <li><b>Color Coding</b>: Indicates signal quality (green for good, yellow for fair, red for poor)</li>
            <li><b>Brain Regions</b>: Color-shaded areas showing different regions (frontal, central, parietal, occipital)</li>
        </ul>

        <p>This visualization helps you quickly identify electrodes with poor contact or excessive noise.
        It's particularly useful during the setup phase to ensure good signal quality before recording.</p>

        <p>The position of electrodes follows the international 10-20 system naming convention,
        where names indicate location (e.g., F = Frontal, C = Central, P = Parietal, O = Occipital)
        and numbers indicate hemisphere (odd = left, even = right, z = midline).</p>
        """,
    },
    "multi_modality": {
        "title": "Multi-Modality Visualization",
        "content": """
        <h3>Multi-Modality Visualization</h3>
        <p>This visualization allows you to view different types of biosignals simultaneously.</p>

        <h4>Available Modalities:</h4>
        <ul>
            <li><b>EEG</b>: Brain electrical activity</li>
            <li><b>EMG</b>: Muscle electrical activity</li>
            <li><b>ECG</b>: Heart electrical activity</li>
            <li><b>EOG</b>: Eye movement electrical activity</li>
            <li><b>EDA/GSR</b>: Electrodermal activity/Galvanic skin response (sweat gland activity)</li>
            <li><b>PPG</b>: Photoplethysmography (blood volume changes)</li>
            <li><b>Accelerometer</b>: Movement measurement</li>
            <li><b>Gyroscope</b>: Rotational movement measurement</li>
        </ul>

        <p>Each modality is displayed with an appropriate time scale and visualization style.
        Not all modalities are available on all devices - the selector will only show
        modalities that your connected device supports.</p>

        <p>Viewing multiple modalities simultaneously can help identify relationships between
        different physiological signals and detect artifacts (e.g., muscle activity affecting EEG).</p>
        """,
    },
    # Recording Section
    "recording": {
        "title": "Data Recording",
        "content": """
        <h3>Data Recording</h3>
        <p>This section controls saving the incoming EEG data to a file for later analysis.</p>

        <h4>Options:</h4>
        <ul>
            <li><b>Raw Data</b>: Saves the unprocessed signal directly from the device</li>
            <li><b>Processed Data</b>: Saves the data after applying filters and processing</li>
            <li><b>Both</b>: Simultaneously saves both raw and processed data to separate files with "_raw" and "_processed" suffixes</li>
        </ul>

        <p>The recorded data is saved in CSV format, which can be loaded back using the Playback File Board
        or imported into other analysis software like MATLAB, Python, or specialized EEG analysis tools.</p>

        <h4>Markers:</h4>
        <p>You can add event markers to the data stream to tag significant events during recording.
        These markers are stored in a special marker channel and can be used to segment the data
        during analysis (e.g., to mark experiment conditions, stimuli, or observations).</p>

        <p>Marker values can range from 1-255, and you can define their meaning for your specific
        experimental protocol.</p>
        """,
    },
    # Advanced Processing Section
    "ica": {
        "title": "Independent Component Analysis (ICA)",
        "content": """
        <h3>Independent Component Analysis (ICA)</h3>
        <p>ICA is a computational method for separating a multivariate signal into
        additive, independent non-Gaussian signals.</p>

        <h4>In EEG processing, ICA is commonly used for:</h4>
        <ul>
            <li><b>Artifact Removal</b>: Identifying and removing components related to eye blinks, muscle activity, etc.</li>
            <li><b>Source Separation</b>: Isolating different brain activity sources</li>
            <li><b>Signal Cleaning</b>: Separating brain signals from noise</li>
        </ul>

        <h4>Parameters:</h4>
        <ul>
            <li><b>Number of Components</b>: How many independent components to extract. Generally, should not exceed the number of channels.</li>
            <li><b>Channel Selection</b>: Which channels to include in the ICA calculation.</li>
        </ul>

        <p>After computing ICA, you can view the separated components to identify which ones
        represent artifacts. In a full analysis workflow, you would then typically remove artifact
        components and reconstruct the signal.</p>

        <p>Note that ICA works best with at least 8-16 EEG channels and may not provide
        meaningful results with fewer channels.</p>
        """,
    },
    "ica_realtime": {
        "title": "Real-time ICA Monitoring",
        "content": """
        <h3>Real-time ICA Monitoring</h3>
        <p>Real-time ICA continuously computes Independent Component Analysis on a sliding window 
        of EEG data, allowing you to monitor brain activity patterns in real-time.</p>

        <h4>How it Works:</h4>
        <ul>
            <li><b>Sliding Window</b>: Maintains a buffer of recent EEG data (2-10 seconds)</li>
            <li><b>Continuous Update</b>: Recomputes ICA components at regular intervals</li>
            <li><b>Live Visualization</b>: Updates the ICA visualization dialog with new components</li>
            <li><b>Optimized Processing</b>: Uses efficient algorithms to minimize computational load</li>
        </ul>

        <h4>Parameters:</h4>
        <ul>
            <li><b>Update Interval</b>: How often to recompute ICA (0.5-2.0 seconds)
                <ul>
                    <li>Shorter intervals: More responsive but higher CPU usage</li>
                    <li>Longer intervals: More stable but less responsive</li>
                </ul>
            </li>
            <li><b>Window Size</b>: Amount of data to analyze (2-10 seconds)
                <ul>
                    <li>Smaller windows: Faster computation, less stable results</li>
                    <li>Larger windows: More stable results, slower computation</li>
                </ul>
            </li>
            <li><b>Number of Components</b>: Same as standard ICA (typically 2-8)</li>
            <li><b>Channel Selection</b>: Which channels to include in real-time analysis</li>
        </ul>

        <h4>Use Cases:</h4>
        <ul>
            <li><b>Neurofeedback</b>: Monitor specific brain activity patterns in real-time</li>
            <li><b>Artifact Monitoring</b>: Continuously track and identify artifacts as they occur</li>
            <li><b>Brain State Monitoring</b>: Observe changes in cognitive states during tasks</li>
            <li><b>Research Applications</b>: Real-time analysis during experiments</li>
            <li><b>BCI Development</b>: Component analysis for brain-computer interfaces</li>
        </ul>

        <h4>Performance Considerations:</h4>
        <ul>
            <li><b>CPU Usage</b>: Real-time ICA is computationally intensive</li>
            <li><b>Channel Count</b>: More channels require exponentially more processing power</li>
            <li><b>Update Rate</b>: Faster updates increase CPU load significantly</li>
            <li><b>Memory Usage</b>: Larger windows consume more memory</li>
        </ul>

        <h4>Best Practices:</h4>
        <ul>
            <li>Start with 2-4 components for initial testing</li>
            <li>Use 1-2 second update intervals for most applications</li>
            <li>Select 8-16 channels for optimal balance of information and performance</li>
            <li>Monitor system performance and adjust parameters accordingly</li>
            <li>Ensure good signal quality before enabling real-time mode</li>
        </ul>

        <h4>Limitations:</h4>
        <ul>
            <li><b>Minimum Channels</b>: Requires at least as many channels as components</li>
            <li><b>Data Quality</b>: Poor signal quality affects real-time results significantly</li>
            <li><b>Computational Delay</b>: Some delay is inherent due to processing time</li>
            <li><b>Stability</b>: Results may vary more than static ICA due to shorter data windows</li>
        </ul>

        <p><b>Note:</b> Real-time ICA is primarily for monitoring and research purposes. 
        For final analysis, it's recommended to also perform static ICA on longer data segments.</p>
        """,
    },
    "advanced_filters": {
        "title": "Advanced Digital Filters",
        "content": """
        <h3>Advanced Digital Filters</h3>
        <p>Advanced filtering provides more sophisticated signal processing options beyond basic bandpass filtering, 
        offering different filter types with specific characteristics for various EEG analysis needs.</p>

        <h4>Filter Types:</h4>

        <h5>Butterworth Filters</h5>
        <ul>
            <li><b>Characteristics</b>: Maximally flat frequency response in the passband</li>
            <li><b>Advantages</b>: No ripple in passband, stable and predictable</li>
            <li><b>Best for</b>: General-purpose filtering, standard EEG preprocessing</li>
            <li><b>Recommended</b>: Default choice for most EEG applications</li>
        </ul>

        <h5>Chebyshev Type I Filters</h5>
        <ul>
            <li><b>Characteristics</b>: Sharper cutoff than Butterworth but with ripple in passband</li>
            <li><b>Ripple Parameter</b>: Controls amount of fluctuation in passband (1.0-2.0 dB recommended)</li>
            <li><b>Advantages</b>: Steeper transition between pass and stop bands</li>
            <li><b>Disadvantages</b>: Can be numerically unstable, especially with synthetic data</li>
            <li><b>Best for</b>: Real EEG data when sharp frequency separation is needed</li>
            <li><b>⚠️ Warning</b>: Not recommended for synthetic boards or demonstration data</li>
        </ul>

        <h5>Bessel Filters</h5>
        <ul>
            <li><b>Characteristics</b>: Linear phase response, minimal time-domain distortion</li>
            <li><b>Advantages</b>: Preserves signal waveform shape, good transient response</li>
            <li><b>Best for</b>: Event-related potential (ERP) analysis, spike detection</li>
            <li><b>Trade-off</b>: Less sharp frequency cutoff than other filter types</li>
        </ul>

        <h5>Zero-Phase Variants</h5>
        <ul>
            <li><b>Zero-Phase Filtering</b>: Applies filter forward and backward to eliminate phase distortion</li>
            <li><b>Advantages</b>: No phase shift, symmetric impulse response</li>
            <li><b>Disadvantages</b>: Cannot be used in real-time applications</li>
            <li><b>Best for</b>: Offline analysis where preserving exact timing is critical</li>
        </ul>

        <h4>Filter Parameters:</h4>
        <ul>
            <li><b>Filter Order</b>: Higher orders provide steeper cutoffs but may introduce instability
                <ul>
                    <li>Butterworth/Bessel: 1-10 (typically 4-6)</li>
                    <li>Chebyshev: 2-4 (maximum 4 for stability)</li>
                </ul>
            </li>
            <li><b>Ripple (Chebyshev only)</b>: Amount of fluctuation in passband
                <ul>
                    <li>Lower values: Less ripple but potential instability</li>
                    <li>Recommended range: 1.0-2.0 dB</li>
                    <li>Higher values: More stable but more passband distortion</li>
                </ul>
            </li>
            <li><b>Window Function</b>: Mathematical function applied to filter design
                <ul>
                    <li>No Window: Standard filter design</li>
                    <li>Hanning: Smooth transitions, reduces side lobes</li>
                    <li>Hamming: Similar to Hanning with different characteristics</li>
                    <li>Blackman-Harris: Maximum side lobe suppression</li>
                </ul>
            </li>
        </ul>

        <h4>Channel Selection:</h4>
        <ul>
            <li><b>All Channels</b>: Apply filtering to entire dataset (default)</li>
            <li><b>Selected Channels</b>: Apply only to specific channels of interest</li>
            <li><b>Use Cases</b>: 
                <ul>
                    <li>Focus processing on specific brain regions</li>
                    <li>Preserve unfiltered data in other channels for comparison</li>
                    <li>Reduce computational load</li>
                </ul>
            </li>
        </ul>

        <h4>Application Guidelines:</h4>

        <h5>Standard EEG Preprocessing</h5>
        <ul>
            <li><b>Filter Type</b>: Butterworth</li>
            <li><b>Order</b>: 4-6</li>
            <li><b>Frequency Range</b>: 1-50 Hz (typical)</li>
            <li><b>Reasoning</b>: Stable, predictable, widely accepted</li>
        </ul>

        <h5>Precise Frequency Isolation</h5>
        <ul>
            <li><b>Filter Type</b>: Chebyshev Type I (with real data only)</li>
            <li><b>Order</b>: 3-4</li>
            <li><b>Ripple</b>: 1.0-1.5 dB</li>
            <li><b>Use Case</b>: Isolating specific brain rhythms (alpha, beta bands)</li>
        </ul>

        <h5>ERP/Spike Analysis</h5>
        <ul>
            <li><b>Filter Type</b>: Bessel or Butterworth Zero-Phase</li>
            <li><b>Order</b>: 4-6</li>
            <li><b>Reasoning</b>: Preserves waveform shape and timing</li>
        </ul>

        <h4>Stability and Performance:</h4>
        <ul>
            <li><b>Data Type Considerations</b>:
                <ul>
                    <li>Real EEG data: All filter types generally work well</li>
                    <li>Synthetic data: Butterworth and Bessel recommended</li>
                    <li>Repetitive patterns: Avoid high-order Chebyshev filters</li>
                </ul>
            </li>
            <li><b>Automatic Adjustments</b>: Application automatically adjusts unstable parameters</li>
            <li><b>Error Handling</b>: Graceful fallback to original data if filtering fails</li>
            <li><b>Real-time Performance</b>: All filters work in real-time streaming mode</li>
        </ul>

        <h4>Common Issues and Solutions:</h4>
        <ul>
            <li><b>Filter Instability</b>: Reduce order, increase ripple (Chebyshev), or switch to Butterworth</li>
            <li><b>Frequency Artifacts</b>: Check cutoff frequencies relative to sampling rate</li>
            <li><b>Signal Distortion</b>: Try lower order or different filter type</li>
            <li><b>Poor Performance</b>: Reduce number of selected channels</li>
        </ul>

        <p><b>Recommendation:</b> For most EEG applications, start with Butterworth filters. 
        Only use Chebyshev when you specifically need sharper frequency separation and are working with real EEG data. 
        Always validate your filtering results by comparing before and after signals.</p>
        """,
    },
    "wavelet": {
        "title": "Wavelet Transforms",
        "content": """
        <h3>Wavelet Transforms</h3>
        <p>Wavelet transforms decompose a signal into a set of wavelets at different scales,
        allowing time-frequency analysis of EEG data.</p>

        <h4>Advantages over Fourier transforms:</h4>
        <ul>
            <li>Provides both time and frequency information</li>
            <li>Better represents transient events and non-stationary signals</li>
            <li>Can focus analysis on specific frequency ranges or time points</li>
        </ul>

        <h4>Available Wavelets:</h4>
        
        <h5>Daubechies Wavelets (DB1-DB15)</h5>
        <ul>
            <li><b>DB1 (Haar)</b>: Simplest wavelet, good for step-like features</li>
            <li><b>DB4</b>: Most commonly used, good balance of properties</li>
            <li><b>DB6-DB8</b>: Better frequency resolution, good for EEG analysis</li>
            <li><b>Higher orders</b>: More oscillations, better frequency resolution</li>
        </ul>

        <h5>Biorthogonal Wavelets (BIOR)</h5>
        <ul>
            <li><b>BIOR1_1</b>: Linear reconstruction</li>
            <li><b>BIOR2_2, BIOR2_4</b>: Good for image-like data</li>
            <li><b>BIOR3_3, BIOR3_5</b>: Balanced properties for general use</li>
            <li><b>BIOR4_4</b>: Symmetric, good for signal reconstruction</li>
        </ul>

        <h5>Coiflets Wavelets (COIF1-COIF5)</h5>
        <ul>
            <li>More symmetric than Daubechies</li>
            <li>Good for applications requiring symmetry</li>
            <li>COIF2-COIF3 recommended for EEG</li>
        </ul>

        <h5>Symlets Wavelets (SYM2-SYM10)</h5>
        <ul>
            <li>Nearly symmetric versions of Daubechies</li>
            <li>SYM4-SYM6 good for EEG applications</li>
            <li>Better phase properties than standard Daubechies</li>
        </ul>

        <h4>Parameters:</h4>
        <ul>
            <li><b>Wavelet Type</b>: Choose based on your signal characteristics
                <ul>
                    <li>DB4: General-purpose, widely used for EEG</li>
                    <li>DB6-DB8: Better frequency resolution</li>
                    <li>BIOR wavelets: When reconstruction quality is important</li>
                    <li>SYM wavelets: When phase preservation is critical</li>
                </ul>
            </li>
            <li><b>Decomposition Level</b>: How many levels of detail to decompose (1-8)
                <ul>
                    <li>Level 1: Highest frequencies (finest detail)</li>
                    <li>Higher levels: Lower frequencies (coarser features)</li>
                    <li>Rule of thumb: log2(signal_length) - 1</li>
                </ul>
            </li>
            <li><b>Channel</b>: Which EEG channel to transform</li>
            <li><b>Extension Type</b>: How to handle signal boundaries
                <ul>
                    <li>Symmetric: Reflects signal at boundaries (default)</li>
                    <li>Periodic: Assumes signal is periodic</li>
                </ul>
            </li>
            <li><b>Apply Denoising</b>: Automatically remove noise using wavelet thresholding</li>
        </ul>

        <h4>Applications in EEG:</h4>
        <ul>
            <li><b>Artifact Removal</b>: Identify and remove specific frequency components</li>
            <li><b>Feature Extraction</b>: Extract time-frequency features for classification</li>
            <li><b>Signal Compression</b>: Reduce data size while preserving important features</li>
            <li><b>Event Detection</b>: Detect transient events like spikes or K-complexes</li>
            <li><b>Time-Frequency Analysis</b>: Analyze how frequency content changes over time</li>
        </ul>

        <h4>Workflow:</h4>
        <ol>
            <li><b>Compute Transform</b>: Decompose signal into wavelet coefficients</li>
            <li><b>Analyze Coefficients</b>: Examine time-frequency content</li>
            <li><b>Modify Coefficients</b>: Optional - threshold or modify specific components</li>
            <li><b>Inverse Transform</b>: Reconstruct signal from modified coefficients</li>
        </ol>

        <p>After computing the wavelet transform, you can view the coefficients and apply
        inverse transform to reconstruct the signal using only selected components. This can be used 
        for filtering, denoising, or feature extraction.</p>

        <p>Wavelets are particularly useful for analyzing ERP (Event-Related Potential) components,
        sleep spindles, seizure activity, and other non-stationary EEG features where both time 
        and frequency information are important.</p>
        """,
    },
    # Streaming Tab
    "streamers": {
        "title": "Data Streaming Options",
        "content": """
        <h3>Data Streaming Options</h3>
        <p>This feature allows you to send collected data to files or network destinations in real-time.</p>

        <h4>Streaming Types:</h4>
        <ul>
            <li><b>File Streamer</b>: Writes data to a file in real-time. Format: "file://[filename]:[mode]"
                <ul>
                    <li><i>Mode 'w'</i>: Creates a new file (overwrites existing)</li>
                    <li><i>Mode 'a'</i>: Appends to an existing file</li>
                </ul>
            </li>
            <li><b>Network Streamer</b>: Broadcasts data over a network. Format: "streaming_board://[IP]:[port]"
                <ul>
                    <li>Use multicast addresses (224.0.0.0 to 239.255.255.255) for one-to-many broadcasting</li>
                </ul>
            </li>
        </ul>

        <h4>Use Cases:</h4>
        <ul>
            <li>Creating a real-time backup of recorded data</li>
            <li>Sharing data with another application or computer</li>
            <li>Implementing distributed processing pipelines</li>
            <li>Setting up multi-person EEG experiments with synchronized data</li>
        </ul>

        <p>Note: The streaming feature increases CPU usage and may impact performance.
        Use only when needed, especially on lower-powered computers.</p>
        """,
    },
    "board_config": {
        "title": "Board Configuration",
        "content": """
        <h3>Board Configuration</h3>
        <p>This feature allows you to send device-specific commands to the EEG board.</p>

        <p><b>Warning:</b> These commands directly affect board operation. Only use if you understand
        the specific command syntax for your device.</p>

        <h4>Example Commands for Common Boards:</h4>
        <ul>
            <li><b>OpenBCI Cyton</b>:
                <ul>
                    <li>"x1020000X" - Start streaming</li>
                    <li>"s" - Stop streaming</li>
                    <li>"d" - Set default channel settings</li>
                    <li>"c" - Start calibration</li>
                </ul>
            </li>
            <li><b>Muse</b>: Most commands use JSON format, e.g.:
                <ul>
                    <li>{"command":"start"}</li>
                    <li>{"command":"stop"}</li>
                    <li>{"command":"preset","args":{"preset":"14"}}</li>
                </ul>
            </li>
        </ul>

        <p>Consult your device's documentation for specific command formats and options.
        Incorrect commands may cause unpredictable behavior or require device restart.</p>
        """,
    },
    # MNE Integration
    "mne": {
        "title": "MNE Integration",
        "content": """
        <h3>MNE Integration</h3>
        <p>This feature allows you to convert BrainFlow data to MNE format for advanced neurophysiological analysis.</p>

        <p><a href="https://mne.tools/">MNE-Python</a> is a comprehensive Python library for processing,
        analyzing, and visualizing neurophysiological data (EEG, MEG, etc.).</p>

        <h4>Two-Step Process:</h4>
        <ol>
            <li><b>Data Conversion</b>: Convert current EEG data to MNE Raw format</li>
            <li><b>Visualization</b>: Create advanced plots and analyses using MNE's capabilities</li>
        </ol>

        <h4>Conversion Modes:</h4>
        <ul>
            <li><b>Flexible Mode</b>: Converts all available channels, allows channel selection during visualization</li>
            <li><b>Performance Mode</b>: Converts only selected channels for better performance and memory usage</li>
        </ul>

        <h4>Available Visualizations:</h4>
        <ul>
            <li><b>Power Spectral Density (PSD)</b>: Frequency content analysis with individual or averaged channels</li>
            <li><b>Topomap</b>: Spatial distribution of activity across frequency bands (Alpha, Beta, Theta, etc.)</li>
            <li><b>Raw Data</b>: Time series display with proper scaling and channel separation</li>
            <li><b>Spectrogram</b>: Time-frequency representation of signal changes</li>
        </ul>

        <p>After conversion, you can continue analysis in Python using MNE's full suite of functions
        or export to other formats for further processing in specialized software.</p>
        """,
    },
    "mne_conversion": {
        "title": "MNE Data Conversion",
        "content": """
        <h3>MNE Data Conversion</h3>
        <p>The first step in MNE integration is converting your EEG data from BrainFlow format to MNE's Raw format.</p>

        <h4>Conversion Parameters:</h4>
        <ul>
            <li><b>Data Duration</b>: How many seconds of recent data to convert (1-60 seconds)</li>
            <li><b>Auto Convert to V</b>: Automatically convert from microvolts (μV) to volts (V) as expected by MNE</li>
        </ul>

        <h4>Conversion Modes:</h4>

        <h5>Flexible Mode (Recommended for Analysis)</h5>
        <ul>
            <li>Converts all available EEG channels</li>
            <li>Channel selection happens during visualization</li>
            <li>Allows experimenting with different channel combinations</li>
            <li>Better for exploratory analysis</li>
        </ul>

        <h5>Performance Mode (Optimized for Speed)</h5>
        <ul>
            <li>Converts only pre-selected channels</li>
            <li>Faster conversion and lower memory usage</li>
            <li>Visualization limited to converted channels</li>
            <li>Better for focused analysis or low-resource systems</li>
        </ul>

        <h4>Process:</h4>
        <ol>
            <li>Select conversion mode and parameters</li>
            <li>If using Performance Mode, select specific channels</li>
            <li>Click "Convert to MNE" to start the process</li>
            <li>Monitor progress in the Operation Status section</li>
            <li>Once complete, visualization options become available</li>
        </ol>

        <p><b>Note:</b> Conversion runs in the background, so you can continue using other parts
        of the application while it processes.</p>
        """,
    },
    "mne_visualization": {
        "title": "MNE Visualization Options",
        "content": """
        <h3>MNE Visualization Options</h3>
        <p>After successful data conversion, you can create various types of scientific visualizations
        using MNE's advanced plotting capabilities.</p>

        <h4>Plot Types:</h4>

        <h5>Power Spectral Density (PSD)</h5>
        <ul>
            <li>Shows frequency content of EEG signals</li>
            <li>Individual mode: Each channel as colored line with legend</li>
            <li>Averaged mode: Single line representing average across channels</li>
            <li>Useful for identifying dominant brain rhythms and artifacts</li>
        </ul>

        <h5>Topomap (Spatial Brain Mapping)</h5>
        <ul>
            <li>Shows spatial distribution of power across the scalp</li>
            <li>Choose from predefined frequency bands: Alpha (8-13Hz), Beta (13-30Hz), etc.</li>
            <li>Custom frequency ranges supported</li>
            <li>Single channel: Shows as colored circle</li>
            <li>Multiple channels: Grid layout with relative power intensities</li>
        </ul>

        <h5>Raw Data (Time Series)</h5>
        <ul>
            <li>Displays EEG signals over time</li>
            <li>Each channel shown with offset for clear separation</li>
            <li>Color-coded channels for easy identification</li>
            <li>Useful for visual inspection of signal quality and artifacts</li>
        </ul>

        <h5>Spectrogram (Time-Frequency)</h5>
        <ul>
            <li>Shows how frequency content changes over time</li>
            <li>Uses first selected channel</li>
            <li>Color intensity represents power at each time-frequency point</li>
            <li>Excellent for detecting transient events and state changes</li>
        </ul>

        <h4>Visualization Controls:</h4>
        <ul>
            <li><b>Frequency Range</b>: Set min/max frequencies for analysis (1-100 Hz)</li>
            <li><b>Channel Selection</b>: Choose which channels to display</li>
            <li><b>PSD Mode Toggle</b>: Switch between individual and averaged display</li>
            <li><b>Topomap Bands</b>: Quick selection of common EEG frequency bands</li>
        </ul>

        <p><b>Performance Tips:</b></p>
        <ul>
            <li>Use fewer channels for faster rendering</li>
            <li>Narrow frequency ranges focus analysis and improve clarity</li>
            <li>Individual channel mode works best with ≤16 channels</li>
            <li>Topomap visualization adapts automatically to channel count</li>
        </ul>
        """,
    },
    "mne_workflow": {
        "title": "MNE Integration Workflow",
        "content": """
        <h3>MNE Integration Workflow</h3>
        <p>This guide walks you through the complete process of using MNE integration
        for EEG analysis in the application.</p>

        <h4>Prerequisites:</h4>
        <ul>
            <li>EEG device connected and streaming data</li>
            <li>At least a few seconds of recorded data</li>
            <li>MNE-Python package installed (pip install mne)</li>
        </ul>

        <h4>Step-by-Step Workflow:</h4>

        <h5>1. Data Collection Phase</h5>
        <ol>
            <li>Connect your EEG device in the Connection tab</li>
            <li>Start streaming in the Streaming tab</li>
            <li>Record some baseline data (eyes closed, relaxed state)</li>
            <li>Optionally record task-specific data (eyes open, cognitive tasks, etc.)</li>
        </ol>

        <h5>2. MNE Conversion Phase</h5>
        <ol>
            <li>Navigate to the MNE Integration tab</li>
            <li>Choose conversion mode:
                <ul>
                    <li><b>Flexible Mode</b>: For comprehensive analysis</li>
                    <li><b>Performance Mode</b>: For targeted analysis with specific channels</li>
                </ul>
            </li>
            <li>Set data duration (start with 10 seconds)</li>
            <li>If using Performance Mode, select channels of interest</li>
            <li>Click "Convert to MNE" and wait for completion</li>
        </ol>

        <h5>3. Analysis and Visualization Phase</h5>
        <ol>
            <li>Start with PSD analysis to understand frequency content</li>
            <li>Use Topomap to see spatial distribution of brain activity</li>
            <li>Check Raw Data view for signal quality assessment</li>
            <li>Use Spectrogram for time-varying analysis</li>
            <li>Experiment with different frequency ranges and channel selections</li>
        </ol>

        <h4>Common Analysis Scenarios:</h4>

        <h5>Alpha Wave Detection (Relaxation/Meditation)</h5>
        <ol>
            <li>Record with eyes closed in relaxed state</li>
            <li>Convert 10-30 seconds of data</li>
            <li>Use PSD plot with 8-13 Hz range</li>
            <li>Look for prominent peak around 10 Hz</li>
            <li>Use Alpha topomap to see spatial distribution</li>
        </ol>

        <h5>Artifact Identification</h5>
        <ol>
            <li>Convert data including movement or eye blinks</li>
            <li>Use Raw Data view to visually inspect</li>
            <li>Check PSD for high-frequency noise or low-frequency drift</li>
            <li>Use multiple channels to identify artifact sources</li>
        </ol>

        <h5>Cognitive Load Assessment</h5>
        <ol>
            <li>Record baseline (rest) and task data separately</li>
            <li>Convert both datasets using same parameters</li>
            <li>Compare Beta band (13-30 Hz) activity</li>
            <li>Use topomaps to identify regions of increased activity</li>
        </ol>

        <h4>Best Practices:</h4>
        <ul>
            <li>Always start with good signal quality (green indicators)</li>
            <li>Use consistent recording conditions for comparisons</li>
            <li>Document your experimental conditions</li>
            <li>Start with standard frequency bands before custom ranges</li>
            <li>Validate findings across multiple recordings</li>
        </ul>

        <h4>Troubleshooting:</h4>
        <ul>
            <li><b>Conversion fails</b>: Check if enough data is available</li>
            <li><b>Plot appears empty</b>: Verify frequency range includes signal content</li>
            <li><b>Poor signal quality</b>: Check electrode contact and reduce artifacts</li>
            <li><b>Performance issues</b>: Use Performance Mode with fewer channels</li>
        </ul>
        """,
    },
    "mne_advanced": {
        "title": "Advanced MNE Features",
        "content": """
        <h3>Advanced MNE Features</h3>
        <p>Beyond basic visualization, MNE integration offers advanced capabilities
        for sophisticated EEG analysis.</p>

        <h4>Technical Features:</h4>

        <h5>Asynchronous Processing</h5>
        <ul>
            <li>Conversion and visualization run in background processes</li>
            <li>Application remains responsive during heavy computations</li>
            <li>Multiple tasks can be queued and processed</li>
            <li>Real-time progress monitoring with cancellation support</li>
        </ul>

        <h5>Memory Management</h5>
        <ul>
            <li>Automatic cleanup of completed tasks</li>
            <li>Performance Mode reduces memory footprint</li>
            <li>Efficient handling of large datasets</li>
            <li>Task result caching for quick access</li>
        </ul>

        <h5>Quality Assurance</h5>
        <ul>
            <li>Data validation before conversion</li>
            <li>Error handling with detailed feedback</li>
            <li>Automatic unit conversion (μV to V)</li>
            <li>Channel mapping and naming consistency</li>
        </ul>

        <h4>Integration with MNE Ecosystem:</h4>

        <h5>Export Capabilities</h5>
        <ul>
            <li>Converted data maintains MNE Raw format compatibility</li>
            <li>Can be loaded into Python scripts for further analysis</li>
            <li>Compatible with MNE's preprocessing pipeline</li>
            <li>Supports export to various formats (FIF, EDF, etc.)</li>
        </ul>

        <h5>Advanced Analysis Potential</h5>
        <p>After conversion, data can be used with MNE's full capabilities:</p>
        <ul>
            <li><b>Preprocessing</b>: Advanced filtering, bad channel detection, ICA</li>
            <li><b>Time-Frequency</b>: Morlet wavelets, multitaper methods</li>
            <li><b>Connectivity</b>: Coherence, phase-locking value, PLI</li>
            <li><b>Source Analysis</b>: Forward modeling, inverse solutions</li>
            <li><b>Statistics</b>: Cluster-based permutation tests</li>
            <li><b>Machine Learning</b>: Feature extraction, classification</li>
        </ul>

        <h4>Performance Optimization:</h4>

        <h5>When to Use Performance Mode</h5>
        <ul>
            <li>Working with high-density EEG systems (64+ channels)</li>
            <li>Limited system memory or processing power</li>
            <li>Focused analysis on specific brain regions</li>
            <li>Real-time or near-real-time processing requirements</li>
        </ul>

        <h5>When to Use Flexible Mode</h5>
        <ul>
            <li>Exploratory data analysis</li>
            <li>Comparing different channel combinations</li>
            <li>Educational or demonstration purposes</li>
            <li>Systems with adequate memory and processing power</li>
        </ul>

        <h4>Scientific Applications:</h4>
        <ul>
            <li><b>Neurofeedback</b>: Real-time monitoring of specific frequency bands</li>
            <li><b>BCI Research</b>: Feature extraction for brain-computer interfaces</li>
            <li><b>Clinical Assessment</b>: Quantitative EEG analysis</li>
            <li><b>Cognitive Neuroscience</b>: Event-related potential analysis</li>
            <li><b>Sleep Research</b>: Sleep stage classification</li>
            <li><b>Meditation Studies</b>: Alpha/theta wave analysis</li>
        </ul>

        <h4>Future Enhancements:</h4>
        <p>The MNE integration is designed to be extensible. Potential future features include:</p>
        <ul>
            <li>Real-time streaming analysis</li>
            <li>Automated artifact detection and removal</li>
            <li>Integration with machine learning models</li>
            <li>Advanced source localization</li>
            <li>Group-level statistical analysis</li>
        </ul>
        """,
    },
    # General EEG Concepts
    "eeg_basics": {
        "title": "EEG Basics",
        "content": """
        <h3>EEG Basics</h3>
        <p>Electroencephalography (EEG) records electrical activity generated by synchronized activity
        of neurons in the brain.</p>

        <h4>Key Concepts:</h4>
        <ul>
            <li><b>Channels</b>: Individual recording sites on the scalp, named according to brain region</li>
            <li><b>Sampling Rate</b>: Number of data points recorded per second (Hz)</li>
            <li><b>Amplitudes</b>: Typically measured in microvolts (μV)</li>
        </ul>

        <h4>Brain Rhythms:</h4>
        <ul>
            <li><b>Delta (0.5-4 Hz)</b>: Deep sleep, unconsciousness</li>
            <li><b>Theta (4-8 Hz)</b>: Drowsiness, meditation, memory processing</li>
            <li><b>Alpha (8-13 Hz)</b>: Relaxed wakefulness, eyes closed</li>
            <li><b>Beta (13-30 Hz)</b>: Active thinking, focus, alert states</li>
            <li><b>Gamma (>30 Hz)</b>: Higher cognitive processing, perception</li>
        </ul>

        <h4>Artifacts:</h4>
        <ul>
            <li><b>Muscular</b>: From facial expressions, neck tension, etc.</li>
            <li><b>Ocular</b>: Eye blinks and movements</li>
            <li><b>Cardiac</b>: Heart rhythm interference</li>
            <li><b>Environmental</b>: Power line noise (50/60 Hz)</li>
            <li><b>Movement</b>: Electrode displacement, cable movement</li>
        </ul>

        <p>EEG signal processing typically involves filtering, artifact removal, and
        frequency analysis to extract meaningful information about brain states.</p>
        """,
    },
}


class HelpDialog(QDialog):
    """Dialog window that displays contextual help information."""

    def __init__(
        self, title: str, content: str, parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize the help dialog with title and content.

        Args:
            title: The title of the help dialog
            content: HTML content to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(f"Help: {title}")
        self.setMinimumSize(600, 400)
        self.setup_ui(content)

    def setup_ui(self, content: str) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Create HTML content viewer
        self.content_browser = QTextBrowser()
        self.content_browser.setHtml(content)
        self.content_browser.setOpenExternalLinks(True)

        # Use a more readable font
        font = QFont("Arial", 10)
        self.content_browser.setFont(font)

        layout.addWidget(self.content_browser)

        # Add close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)


class HelpButton(QPushButton):
    """Custom help button that shows contextual help when clicked."""

    def __init__(self, help_key: str, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the help button.

        Args:
            help_key: Key to look up help content
            parent: Parent widget
        """
        super().__init__(parent)
        self.help_key = help_key
        self.setFixedSize(QSize(20, 20))
        self.setText("?")
        self.setToolTip("Click for help")

        # Style the button to look like a help icon
        self.setStyleSheet(
            """
            QPushButton {
                border-radius: 5px;
                background-color: #007ACC;
                color: white;
                font-weight: bold;
                min-height: 10px;
                max-height: 10px;
            }
            QPushButton:hover {
                background-color: #009AEE;
            }
        """
        )

        self.clicked.connect(self.show_help)

    def show_help(self) -> None:
        """Show help dialog with content for this button's help key."""
        if self.help_key in HELP_CONTENT:
            help_item = HELP_CONTENT[self.help_key]
            dialog = HelpDialog(help_item["title"], help_item["content"], self.parent())
            dialog.exec_()
        else:
            print(f"Help content not found for key: {self.help_key}")


class EEGConceptsHelpDialog(QDialog):
    """Dialog with comprehensive help on EEG concepts and application usage."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the comprehensive help dialog."""
        super().__init__(parent)
        self.setWindowTitle("EEG Processor Help")
        self.setMinimumSize(800, 600)
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the comprehensive help UI with tabs."""
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tabs = QTabWidget()

        # Add tabs for different help categories
        self.add_tab("EEG Basics", ["eeg_basics"])
        self.add_tab(
            "Hardware", ["board_selection", "connection_params", "preset_selection"]
        )
        self.add_tab(
            "Signal Processing",
            ["bandpass_filter", "notch_filter", "denoising", "detrend"],
        )
        self.add_tab(
            "Visualization", ["eeg_visualization", "brain_map", "multi_modality"]
        )
        self.add_tab("Recording", ["recording", "streaming", "streamers"])
        self.add_tab("Advanced Analysis", ["ica", "ica_realtime", "advanced_filters", "wavelet", "downsampling"])
        # Add comprehensive MNE Integration tab
        self.add_tab(
            "MNE Integration",
            [
                "mne",
                "mne_conversion",
                "mne_visualization",
                "mne_workflow",
                "mne_advanced",
            ],
        )

        layout.addWidget(self.tabs)

        # Add close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def add_tab(self, tab_name: str, help_keys: list[str]) -> None:
        """Add a tab with specified help content."""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)

        # Create a scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Add all help content for this tab
        for key in help_keys:
            if key in HELP_CONTENT:
                help_item = HELP_CONTENT[key]

                # Create text browser for this item
                browser = QTextBrowser()
                browser.setHtml(help_item["content"])
                browser.setOpenExternalLinks(True)

                # Use a more readable font
                font = QFont("Arial", 10)
                browser.setFont(font)

                content_layout.addWidget(browser)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        tab_layout.addWidget(scroll)

        self.tabs.addTab(tab, tab_name)


def show_help_topic(key: str, parent: Optional[QWidget] = None) -> None:
    """
    Show help dialog for a specific topic.

    Args:
        key: Help content key
        parent: Parent widget
    """
    if key in HELP_CONTENT:
        help_item = HELP_CONTENT[key]
        dialog = HelpDialog(help_item["title"], help_item["content"], parent)
        dialog.exec_()
    else:
        print(f"Help content not found for key: {key}")


def show_eeg_concepts_help(parent: Optional[QWidget] = None) -> None:
    """
    Show comprehensive EEG concepts help dialog.

    Args:
        parent: Parent widget
    """
    dialog = EEGConceptsHelpDialog(parent)
    dialog.exec_()