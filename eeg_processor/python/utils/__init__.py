"""
Utilities Package for EEG Processor Application.

This package provides essential utility components and support systems for the EEG
processing application, including theme management, comprehensive help system, and
common functionality used across the application.

Core Utilities:

- ThemeManager: Advanced application styling and theme management
  * Professional dark theme implementation with comprehensive Qt widget styling
  * Consistent color scheme across all application components (panels, dialogs, widgets)
  * Predefined color palette for status indicators (success, warning, error, accent)
  * Comprehensive Qt stylesheet covering all widget types with hover and disabled states
  * Professional appearance optimized for long-term usage and reduced eye strain
  * Consistent visual hierarchy with proper contrast ratios and accessibility considerations

- HelpSystem: Comprehensive contextual help and documentation system
  * Modular help content dictionary with 25+ detailed topics covering all application aspects
  * Context-sensitive help buttons (HelpButton) integrated throughout the UI
  * Comprehensive help dialogs with HTML content rendering and external link support
  * Tabbed help interface (EEGConceptsHelpDialog) organizing information by functional areas
  * Educational content covering EEG basics, signal processing theory, and advanced analysis
  * Practical guidance for hardware setup, parameter configuration, and troubleshooting

Help System Features:

Comprehensive Topic Coverage:
- EEG Fundamentals: Brain rhythms, artifacts, basic concepts, and measurement principles
- Hardware Configuration: Board selection, connection parameters, preset management
- Signal Processing: Bandpass/notch filtering, detrending, wavelet denoising theory and practice
- Visualization: EEG plots, brain mapping, multi-modality displays, interaction techniques
- Recording: Data storage, marker insertion, streaming configuration, file management
- Advanced Analysis: ICA theory and practice, real-time monitoring, advanced filtering
- MNE Integration: Complete workflow guidance, conversion modes, visualization options

Educational Content Quality:
- Theoretical background with practical application guidance
- Parameter recommendations based on common use cases and best practices
- Troubleshooting guides with common issues and solutions
- Scientific context explaining why specific settings are recommended
- Progressive complexity from basic concepts to advanced research applications

User Experience Features:
- Context-sensitive help buttons positioned near relevant controls
- Quick access help topics for immediate assistance during operation
- Comprehensive help dialog with searchable, organized content across functional tabs
- Professional HTML rendering with proper formatting, lists, and hierarchical organization
- Cross-referenced topics with logical information architecture

Theme Management Features:

Visual Design System:
- Professional dark theme optimized for extended use and reduced eye strain
- Consistent color palette with semantic meaning (accent, success, warning, error colors)
- Comprehensive styling covering all Qt widget types and states
- Proper contrast ratios ensuring accessibility and readability
- Modern, professional appearance suitable for research and clinical environments

Qt Widget Styling:
- Complete coverage: buttons, inputs, dropdowns, checkboxes, tabs, scrollbars, groups
- State-specific styling: normal, hover, pressed, disabled, selected states
- Consistent spacing, padding, and border radius for unified appearance
- Color-coded status indicators and interactive feedback
- Professional button styling with proper hover states and accessibility

Technical Implementation:

Modular Architecture:
- Help content organized in structured dictionary format for easy maintenance
- Separation of content from presentation enabling easy updates and translations
- Reusable help button component for consistent integration across UI panels
- Theme manager with centralized color definitions and styling rules

Integration Capabilities:
- Seamless integration with PyQt5 application architecture
- Support for HTML content rendering with external links and rich formatting
- Dynamic help content delivery based on context and user interaction
- Professional dialog management with proper parent-child relationships

Accessibility and Usability:
- Keyboard navigation support for help dialogs and interactive elements
- Screen reader compatibility through proper Qt accessibility attributes
- Consistent visual hierarchy with clear information organization
- User-friendly error handling with helpful guidance and recovery suggestions

Educational Value:
- Scientifically accurate explanations of EEG principles and signal processing concepts
- Practical guidance bridging theory and application for users with varying expertise
- Progressive learning support from basic setup to advanced research applications
- Best practices and recommendations based on established neuroscience protocols

Maintenance and Extension:
- Modular content structure enabling easy addition of new help topics
- Centralized styling definitions for consistent theme management across updates
- Clean separation between utility functions and application-specific implementations
- Documentation standards supporting collaborative development and knowledge transfer

The utilities package provides essential infrastructure supporting the entire EEG
processing application with professional presentation, comprehensive user guidance,
and maintainable architecture designed for both novice users and advanced researchers.
"""

from .help_system import (
    HELP_CONTENT,
    HelpDialog,
    HelpButton,
    EEGConceptsHelpDialog,
    show_help_topic,
    show_eeg_concepts_help,
)
from .theme_manager import ThemeManager

__all__ = [
    # Theme management
    "ThemeManager",
    # Help system components
    "HELP_CONTENT",
    "HelpDialog",
    "HelpButton",
    "EEGConceptsHelpDialog",
    "show_help_topic",
    "show_eeg_concepts_help",
]
