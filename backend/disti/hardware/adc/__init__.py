"""Analog-to-digital converter adapters."""

from .ads1115 import ADCReading, ADS1115Error, ADS1115Reader
from .base import ADCReader

__all__ = ["ADCReader", "ADCReading", "ADS1115Error", "ADS1115Reader"]
