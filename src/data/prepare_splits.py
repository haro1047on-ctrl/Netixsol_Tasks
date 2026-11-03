"""
src/data/prepare_splits.py
==========================
Stratified Dataset Splitting, Golden Test Set Isolation, and Hugging Face Hub Export.
Creates:
1. data/splits/golden_test_200.jsonl: Exactly 200 high-fidelity, category-balanced test records
   strictly isolated and excluded from training.
2. data/splits/train.jsonl: ~85% of remaining cleaned records.
3. data/splits/val.jsonl: ~15% of remaining cleaned records.
4. Optional Hugging Face Dataset push via huggingface_hub.
"""

import argparse
from collections import defaultdict
import json
import logging
import os
from pathlib import Path
import random
import sys
from typing import Dict, List, Set

# Add root directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data.schemas import IntentEnum, TrainingConversation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrepareSplits")


def load_dataset(file_path: str) -> List[TrainingConversation]:
    """Loads JSONL dataset into TrainingConversation objects."""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                records.append(TrainingConversation(**item))
    logger.info(f"Loaded {len(records)} records from {file_path}")
    return records


def save_split(records: List[TrainingConversation], file_path: str) -> None:
    """Saves records to JSONL."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(r.model_dump_json() + "\n")
    logger.info(f"Wrote {len(records)} records to {file_path}")


def create_stratified_splits(
    records: List[TrainingConversation],
    golden_test_size: int = 200,
    val_ratio: float = 0.15,
    random_seed: int = 42,
) -> Dict[str, List[TrainingConversation]]:
    """
    Carves out an isolated Golden Test Set, then creates stratified
    Train and Validation splits across all banking categories.
    """
    random.seed(random_seed)

    # Group by category
    by_category = defaultdict(list)
    for r in records:
        by_category[r.category].append(r)

    golden_test: List[TrainingConversation] = []
    pool: List[TrainingConversation] = []

    # 1. Carve out exactly golden_test_size examples proportionally across categories
    categories = list(by_category.keys())
    per_cat_golden = golden_test_size // len(categories)

    golden_query_texts: Set[str] = set()

    for cat, items in by_category.items():
        random.shuffle(items)
        take_golden = min(per_cat_golden, len(items))
        for item in items[:take_golden]:
            user_msg = next((m.content.strip().lower() for m in item.messages if m.role == "user"), "")
            golden_test.append(item)
            if user_msg:
                golden_query_texts.add(user_msg)
        pool.extend(items[take_golden:])

    # Top up golden_test to exactly golden_test_size if needed
    if len(golden_test) < golden_test_size:
        remaining_needed = golden_test_size - len(golden_test)
        for item in pool[:remaining_needed]:
            user_msg = next((m.content.strip().lower() for m in item.messages if m.role == "user"), "")
            golden_test.append(item)
            if user_msg:
                golden_query_texts.add(user_msg)
        pool = pool[remaining_needed:]

    # STRICT DATA LEAKAGE PREVENTION:
    # Purge any record from the training/validation pool whose user query matches any golden test query
    purged_pool = []
    for item in pool:
        user_msg = next((m.content.strip().lower() for m in item.messages if m.role == "user"), "")
        if user_msg not in golden_query_texts:
            purged_pool.append(item)

    pool = purged_pool

    logger.info(f"Isolated Golden Test Set: {len(golden_test)} records strictly excluded from training.")
    logger.info(f"Remaining clean pool after zero-leakage query purge: {len(pool)} records.")

    # 2. Stratified Train / Validation Split on Remaining Pool
    pool_by_category = defaultdict(list)
    for r in pool:
        pool_by_category[r.category].append(r)

    train_set: List[TrainingConversation] = []
    val_set: List[TrainingConversation] = []

    for cat, items in pool_by_category.items():
        random.shuffle(items)
        val_count = max(1, int(len(items) * val_ratio))
        val_set.extend(items[:val_count])
        train_set.extend(items[val_count:])

    random.shuffle(train_set)
    random.shuffle(val_set)
    random.shuffle(golden_test)

    return {
        "train": train_set,
        "val": val_set,
        "golden_test": golden_test,
    }


def push_to_huggingface_hub(
    train_path: str,
    val_path: str,
    golden_path: str,
    repo_id: str,
    token: str,
) -> bool:
    """Pushes the generated splits to a private or public Hugging Face Dataset repo."""
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        logger.info(f"Pushing splits to Hugging Face Dataset repository: {repo_id}...")
        api.create_repo(repo_id=repo_id, repo_type="dataset", token=token, exist_ok=True, private=True)
        api.upload_file(path_or_fileobj=train_path, path_in_repo="train.jsonl", repo_id=repo_id, repo_type="dataset", token=token)
        api.upload_file(path_or_fileobj=val_path, path_in_repo="val.jsonl", repo_id=repo_id, repo_type="dataset", token=token)
        api.upload_file(path_or_fileobj=golden_path, path_in_repo="golden_test_200.jsonl", repo_id=repo_id, repo_type="dataset", token=token)
        logger.info("Successfully uploaded dataset to Hugging Face Hub!")
        return True
    except Exception as e:
        logger.warning(f"Hugging Face upload skipped or failed: {e}. Dataset splits remain fully saved locally.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Create train/val/golden_test splits.")
    parser.add_argument("--input-file", type=str, default="data/processed/cleaned_dataset.jsonl")
    parser.add_argument("--output-dir", type=str, default="data/splits")
    parser.add_argument("--golden-size", type=int, default=200)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--repo-id", type=str, default=os.getenv("HUGGINGFACE_REPO_ID", "zarya-bank/urdulish-banking-sft"))
    parser.add_argument("--hf-token", type=str, default=os.getenv("HUGGINGFACE_TOKEN", ""))
    parser.add_argument("--push-hub", action="store_true", default=False)
    args = parser.parse_args()

    # Safe Windows console encoding
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    records = load_dataset(args.input_file)
    splits = create_stratified_splits(
        records=records,
        golden_test_size=args.golden_size,
        val_ratio=args.val_ratio,
    )

    out_dir = Path(args.output_dir)
    train_path = out_dir / "train.jsonl"
    val_path = out_dir / "val.jsonl"
    golden_path = out_dir / "golden_test_200.jsonl"

    save_split(splits["train"], str(train_path))
    save_split(splits["val"], str(val_path))
    save_split(splits["golden_test"], str(golden_path))

    if args.push_hub and args.hf_token:
        push_to_huggingface_hub(
            train_path=str(train_path),
            val_path=str(val_path),
            golden_path=str(golden_path),
            repo_id=args.repo_id,
            token=args.hf_token,
        )

    print("\n" + "=" * 60)
    print("[SPLITS READY] DATASET STRATIFICATION & SPLIT SUMMARY")
    print("=" * 60)
    print(f"Training Split (train.jsonl)        : {len(splits['train']):,} records")
    print(f"Validation Split (val.jsonl)        : {len(splits['val']):,} records")
    print(f"Isolated Golden Test (golden_200)   : {len(splits['golden_test']):,} records")
    print(f"Total Preserved Dataset Pool        : {len(records):,} records")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
