import asyncio
import csv
import logging
import os
import sys
from pathlib import Path
from code.config import CLAIMS_CSV, OUTPUT_CSV, ACTIVE_PROVIDER
from code.dataloader import iter_claims
from code.engine import VerificationEngine
from code.schema import OutputRow, VLMDecision

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def process_single_claim(context, engine):
    """Processes a single claim directly through the engine."""
    logger.info(f"Processing claim for user {context.user_id}")
    
    # Run Engine directly, skipping the summarization to save cost and preserve context
    decision = await engine.process_claim(context)
        
    # Reconstruct original relative paths for the output.csv 
    # Example format: "images/test/case_001/img_1.jpg"
    original_relative_paths = []
    if context.image_paths:
        for p in context.image_paths:
            # We assume images are inside dataset/images/ and we want to keep it relative 
            # to the dataset root or whatever format it was originally in.
            # To be perfectly safe, let's just find the substring starting with "images/"
            path_str = str(p)
            idx = path_str.find("images/")
            if idx != -1:
                original_relative_paths.append(path_str[idx:])
            else:
                original_relative_paths.append(Path(p).name)

    return OutputRow.from_decision(
        user_id=context.user_id,
        image_paths=";".join(original_relative_paths) if original_relative_paths else "none",
        user_claim=context.user_claim, 
        claim_object=context.claim_object,
        decision=decision
    )

async def main(input_csv: str = CLAIMS_CSV, output_csv: str = OUTPUT_CSV):
    logger.info(f"Starting verification pipeline with provider: {ACTIVE_PROVIDER}")
    
    engine = VerificationEngine(provider=ACTIVE_PROVIDER, use_cache=True, max_concurrent=10)
    
    tasks = []
    for context in iter_claims(claims_csv_path=input_csv):
        tasks.append(process_single_claim(context, engine))
        
    logger.info(f"Queued {len(tasks)} claims. Executing pipeline...")
    
    # Gather all tasks concurrently (managed safely by our RequestManager semaphore)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = 0
    with open(output_csv, mode='w', encoding='utf-8', newline='') as f:
        # Strictly define headers in the required order
        headers = [
            "user_id", "image_paths", "user_claim", "claim_object",
            "evidence_standard_met", "evidence_standard_met_reason",
            "risk_flags", "issue_type", "object_part", "claim_status",
            "claim_status_justification", "supporting_image_ids",
            "valid_image", "severity"
        ]
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Critical task failure during execution: {res}")
            else:
                # Dump Pydantic model and filter out internal tracking fields (e.g. cited_paths)
                row_dict = res.model_dump()
                filtered_row = {k: row_dict[k] for k in headers}
                writer.writerow(filtered_row)
                success_count += 1
                
    logger.info(f"Pipeline complete. Successfully wrote {success_count} rows to {output_csv}.")

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else CLAIMS_CSV
    output_file = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_CSV
    
    asyncio.run(main(input_csv=input_file, output_csv=output_file))
