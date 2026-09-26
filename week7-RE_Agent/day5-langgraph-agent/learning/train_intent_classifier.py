import logging
from pprint import pprint
import sys
from pathlib import Path

# Add parent dir to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from learning.intent_classifier import train

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrainIntentClassifier")

if __name__ == "__main__":
    logger.info("Starting ML intent classifier training...")
    result = train(save=True)
    if result:
        logger.info(f"Training completed. Total samples: {result['n_samples']}")
        logger.info(f"Model accuracy: {result['accuracy']:.2f}")
        logger.info("Classification Report:")
        pprint(result['report'])
    else:
        logger.warning("Training aborted. Not enough data or classes.")
