"""
Business rules configuration for dealer analytics.
Adjust these thresholds to match your interview / business requirements.
"""

# Profit margin rules
MIN_HEALTHY_MARGIN_PCT = 10.0
LOW_MARGIN_WARNING_PCT = 5.0
NEGATIVE_MARGIN_CRITICAL = True  # Flag negative margin as critical

# Stock turnover rules (days)
SLOW_TURNOVER_DAYS = 90
CRITICAL_TURNOVER_DAYS = 120

# Activity rules
INACTIVE_DAYS_THRESHOLD = 45  # No order in this many days = inactive warning
MIN_ORDER_COUNT_LOW_ACTIVITY = 30

# Output paths
DATA_DIR = "data"
OUTPUT_DIR = "output"
DEALERS_CSV = "dealers_sample.csv"
RESULTS_JSON = "processed_results.json"
