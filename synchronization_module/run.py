"""
Run script for the synchronization module.

This script provides the main entry point for running the unified
BCI dataset creator application.
"""
import os
import sys
import argparse
import logging
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.synchronization_app import run_synchronization_app


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BCI Dataset Creator - Unified Synchronization Application"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level"
    )
    
    parser.add_argument(
        "--precision",
        type=float,
        default=1.0,
        help="Default synchronization precision in milliseconds"
    )
    
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Start application in fullscreen mode"
    )
    
    return parser.parse_args()


def setup_logging(level: str) -> None:
    """Setup application logging."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('synchronization_app.log')
        ]
    )


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting BCI Dataset Creator application")
    logger.info(f"Synchronization precision: {args.precision}ms")
    
    try:
        # Run the application
        exit_code = run_synchronization_app()
        logger.info(f"Application exited with code: {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())