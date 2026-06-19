import csv
from typing import Dict, Iterator, List
from pydantic import BaseModel
from code.config import CLAIMS_CSV, USER_HISTORY_CSV, DATASET_DIR

class ClaimContext(BaseModel):
    """
    Unified model holding all context for a specific claim.
    """
    user_id: str
    image_paths: List[str]
    user_claim: str
    claim_object: str
    history_flags: str
    history_summary: str

def load_user_history(history_csv_path: str = USER_HISTORY_CSV) -> Dict[str, Dict[str, str]]:
    """
    Reads the user_history.csv and returns a dictionary mapping user_id to their history data.
    """
    history_map = {}
    with open(history_csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_id = row['user_id']
            history_map[user_id] = {
                'history_flags': row.get('history_flags', ''),
                'history_summary': row.get('history_summary', '')
            }
    return history_map

def iter_claims(claims_csv_path: str = CLAIMS_CSV, history_csv_path: str = USER_HISTORY_CSV) -> Iterator[ClaimContext]:
    """
    Generator that yields coupled ClaimContext objects for each row in claims.csv.
    """
    history_map = load_user_history(history_csv_path)
    
    with open(claims_csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_id = row['user_id']
            
            # Parse semicolon-separated image paths and resolve to absolute paths
            raw_image_paths = row.get('image_paths', '')
            image_paths = [
                str(DATASET_DIR / p.strip()) 
                for p in raw_image_paths.split(';') if p.strip()
            ]
            
            # Clean text fields
            user_claim = row.get('user_claim', '').strip()
            claim_object = row.get('claim_object', '').strip()
            
            # Lookup user history with safe defaults
            user_history = history_map.get(user_id, {
                'history_flags': 'none',
                'history_summary': 'No history available'
            })
            
            yield ClaimContext(
                user_id=user_id,
                image_paths=image_paths,
                user_claim=user_claim,
                claim_object=claim_object,
                history_flags=user_history['history_flags'],
                history_summary=user_history['history_summary']
            )
