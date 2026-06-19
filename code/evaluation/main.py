import csv
import sys
from pathlib import Path

def parse_set_string(s: str) -> set:
    if not s or s.lower() == "none":
        return set()
    return {x.strip().lower() for x in s.split(";") if x.strip()}

def evaluate(ground_truth_path: str, prediction_path: str):
    try:
        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            gt_reader = csv.DictReader(f)
            gt_data = {row['user_id']: row for row in gt_reader}
    except Exception as e:
        print(f"Error reading ground truth: {e}")
        return

    try:
        with open(prediction_path, 'r', encoding='utf-8') as f:
            pred_reader = csv.DictReader(f)
            pred_data = {row['user_id']: row for row in pred_reader}
    except Exception as e:
        print(f"Error reading prediction: {e}")
        return

    metrics = {
        'evidence_standard_met': {'correct': 0, 'total': 0},
        'valid_image': {'correct': 0, 'total': 0},
        'claim_status': {'correct': 0, 'total': 0},
        'issue_type': {'correct': 0, 'total': 0},
        'object_part': {'correct': 0, 'total': 0},
        'risk_flags': {'correct': 0, 'total': 0},
        'supporting_image_ids': {'correct': 0, 'total': 0},
    }

    evaluated_users = 0
    for user_id, gt_row in gt_data.items():
        if user_id not in pred_data:
            continue
            
        pred_row = pred_data[user_id]
        evaluated_users += 1

        # Direct string comparisons (case-insensitive)
        direct_cols = ['evidence_standard_met', 'valid_image', 'claim_status', 'issue_type', 'object_part']
        for col in direct_cols:
            metrics[col]['total'] += 1
            if str(gt_row.get(col, "")).strip().lower() == str(pred_row.get(col, "")).strip().lower():
                metrics[col]['correct'] += 1

        # Set comparisons for semicolon-separated lists
        set_cols = ['risk_flags', 'supporting_image_ids']
        for col in set_cols:
            metrics[col]['total'] += 1
            gt_set = parse_set_string(gt_row.get(col, ""))
            pred_set = parse_set_string(pred_row.get(col, ""))
            if gt_set == pred_set:
                metrics[col]['correct'] += 1

    print("=" * 50)
    print("EVALUATION REPORT")
    print("=" * 50)
    print(f"Ground Truth File: {ground_truth_path}")
    print(f"Predictions File:  {prediction_path}")
    print(f"Total Rows Evaluated: {evaluated_users} / {len(gt_data)}")
    print("-" * 50)
    
    for col, data in metrics.items():
        if data['total'] > 0:
            accuracy = (data['correct'] / data['total']) * 100
            print(f"{col.ljust(25)}: {accuracy:6.2f}% ({data['correct']}/{data['total']})")
    print("=" * 50)

if __name__ == "__main__":
    gt_file = "dataset/sample_claims.csv"
    pred_file = "output.csv"
    if len(sys.argv) == 3:
        gt_file = sys.argv[1]
        pred_file = sys.argv[2]
    evaluate(gt_file, pred_file)
