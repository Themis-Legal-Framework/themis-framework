"""Constants for Themis agents.

Centralizes magic numbers and configuration values for easier maintenance.
"""

# LLM Token Limits (increased for complex legal analysis)
MAX_TOKENS_DOCUMENT_GENERATION = 16000
MAX_TOKENS_ANALYSIS = 8192
MAX_TOKENS_STRATEGY = 8192
MAX_TOKENS_SYNTHESIS = 4096
MAX_TOKENS_TONE_ANALYSIS = 2000

# Text Processing Thresholds
MIN_SUMMARY_LENGTH = 50  # Minimum chars for a summary to be useful
MIN_SENTENCE_LENGTH = 15  # Minimum chars for a sentence to be considered meaningful
MIN_EXTRACTED_FACTS = 3  # Minimum facts needed for meaningful analysis
MIN_DATES_FOR_TIMELINE = 2  # Minimum dates to construct a timeline

# Document Validation
MIN_DOCUMENT_WORDS = 100
MAX_DOCUMENT_WORDS = 10000
MIN_SECTIONS_FOR_VALID_DOC = 3
MAX_WARNINGS_FOR_VALID_DOC = 3

# Party Normalization
MIN_PARTIES_FOR_DEFENDANT = 2  # Need at least 2 parties to assign defendant
