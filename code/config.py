import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Absolute Paths
CODE_DIR = Path(__file__).resolve().parent
ROOT_DIR = CODE_DIR.parent

DATASET_DIR = ROOT_DIR / "dataset"
CLAIMS_CSV = DATASET_DIR / "claims.csv"
SAMPLE_CLAIMS_CSV = DATASET_DIR / "sample_claims.csv"
USER_HISTORY_CSV = DATASET_DIR / "user_history.csv"
EVIDENCE_REQUIREMENTS_CSV = DATASET_DIR / "evidence_requirements.csv"

IMAGES_DIR = DATASET_DIR / "images"
SAMPLE_IMAGES_DIR = IMAGES_DIR / "sample"
TEST_IMAGES_DIR = IMAGES_DIR / "test"

OUTPUT_CSV = ROOT_DIR / "output.csv"
CACHE_DIR = ROOT_DIR / ".cache"

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Model Names
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Active provider: "openai" | "anthropic" | "gemini"
ACTIVE_PROVIDER = os.getenv("ACTIVE_PROVIDER", "anthropic").lower()
