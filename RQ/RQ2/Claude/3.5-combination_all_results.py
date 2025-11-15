import os
import pandas as pd

#Aggregate of all results

BASE_DIR = "./code/replication/RQ/recruit-results/Claude"
OUTPUT_DIR = "./code/replication/RQ/recruit-results/Claude/all-results"
FNAME = "claude-3-5-haiku_results.csv"

paths = [
    os.path.join(BASE_DIR, f"run_{i:02d}", FNAME)
    for i in range(1, 11)
]

dfs = []
for p in paths:
    if os.path.isfile(p):
        df = pd.read_csv(p)
        run_id = os.path.basename(os.path.dirname(p))
        df.insert(0, "run_id", run_id)
        dfs.append(df)
    else:
        print(f"Error: file not found -> {p}")

combined = pd.concat(dfs, ignore_index=True)

out_path = os.path.join(OUTPUT_DIR, "combined_results.csv")
combined.to_csv(out_path, index=False)
print(f"Saved: {out_path}")
