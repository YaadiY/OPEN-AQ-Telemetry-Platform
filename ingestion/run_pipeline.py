import sys
import time
from datetime import datetime, timezone

from fetch_daily import run_daily_batch

def main():
    start_time = time.time()
    print("=" * 65)
    print(f"📡 OPENAQ DAILY BATCH INGESTION STARTED: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 65)

    try:
        # Run daily sliding window batch (last 48 hours for complete coverage)
        parquet_file = run_daily_batch(hours_window=48)
        if not parquet_file:
            print("⚠️ Pipeline finished with no new records.")
            return

        elapsed = round(time.time() - start_time, 2)
        print("=" * 65)
        print(f"✅ PIPELINE COMPLETED SUCCESSFULLY IN {elapsed}s")
        print("=" * 65)

    except Exception as e:
        print(f"\n❌ Pipeline failed with unexpected exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
