# Resistor Calculator Utility

ComponentBox now focuses on component classification across five classes. The resistor calculator remains in the backend as a small, tested utility for future resistor-specific features.

The utility supports standard 4-band resistor math:

1. First significant digit
2. Second significant digit
3. Multiplier
4. Tolerance

Example:

```text
brown black red gold -> 10 * 100 = 1000 ohms -> 1 kohm +/-5%
```

The decoding logic lives in `backend/app/services/resistor_calculator.py`. It is intentionally separate from the main image-classification endpoint so the project can improve component recognition without changing resistor math.
