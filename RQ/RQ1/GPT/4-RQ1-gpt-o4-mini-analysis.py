import csv, ast, pathlib
import pandas as pd
from scipy import stats
import scikit_posthocs as sp
import re

RESULTS_CSV  = pathlib.Path("./code/replication/RQ/recruit-results/GPT/all-results/combined_results_fixed.csv")
DATASET_DIR  = pathlib.Path("./code/replication/dataset_extraction")       
OUTPUT_TXT = pathlib.Path("./code/replication/RQ/RQ1/GPT/results_gpt-o4-mini_RQ1.txt")
COUNTRIES    = ['US', 'BR', 'IN', 'UK', 'NG']
MAX_DATASET = 100 

def import_response(path_csv):
    with open(path_csv, newline='') as f:
        return [row["Recruit"] for row in csv.DictReader(f)]

def import_login(path_csv):
    out = []
    with open(path_csv, newline='') as f:
        for row in csv.DictReader(f):
            raw = row["login"].strip()
            logins = [tok.strip() for tok in raw.split(",") if tok.strip()]
            out.append(logins)
    return out


def filter_six(data, login_id):
    bad = []
    for i, row in enumerate(login_id):
        if sum(1 for login in row if login in data[i]) != 6:
            bad.append(i)
    return bad


def make_score(data, login_id, to_filter):
    score = {c: [] for c in COUNTRIES}
    for i, row in enumerate(login_id):
        if i in to_filter or i+1 > MAX_DATASET:
            continue           
        chosen = [1 if lg in data[i] else 0 for lg in row]
        df = pd.read_csv(DATASET_DIR / f"dataset_{i+1:03d}.csv")

        s_tmp = {c: 0 for c in COUNTRIES}
        for j, login in enumerate(row):
            if not chosen[j]:
                continue
            country = df.loc[df["login"] == login, "country"].values[0]
            s_tmp[country] += 1
        for c in COUNTRIES:
            score[c].append(s_tmp[c])
    return score

# --------------------  RQ1 -----------------------------------------

if __name__ == "__main__":
    if not RESULTS_CSV.exists():
        raise FileNotFoundError(f"{RESULTS_CSV} not found")

    data_resp  = import_response(RESULTS_CSV)
    data_login = import_login(RESULTS_CSV)
    filt_idx   = filter_six(data_resp, data_login)

    with open(OUTPUT_TXT, "w", encoding="utf-8") as fout:
        def log(msg=""):
            print(msg)
            fout.write(msg + "\n")

        # DEBUG 
        log(f"\n[DEBUG] Rows Excluded: {len(filt_idx)}\n")
        for idx in filt_idx:
            log(f"--- Row {idx} ---")
            log(f"Login : {data_login[idx]}")
            log(f"Recruit: {data_resp[idx]}")
            log("")

        score = make_score(data_resp, data_login, filt_idx)

        count_perc = {c: [score[c].count(k) for k in (0,1,2)] for c in COUNTRIES}

        log("[Result for RQ1]")
        for k in (2,1,0):
            log(f"{k} candidate")
            for c in COUNTRIES:
                tot  = sum(count_perc[c])
                perc = count_perc[c][k] / tot * 100 if tot else 0
                log(f"  {c}: {perc:.0f}%")
            log("")


        log("Kruskal-Wallis test:")
        _, p_kw = stats.kruskal(*(score[c] for c in COUNTRIES))
        log(f"p = {p_kw:.14f}")
        if p_kw < 0.05:
            log(f"{p_kw:.14f} < 0.05 → significant difference;")
            log("")
            log("Dunn’s post-hoc (Bonferroni):")
            dunn = sp.posthoc_dunn([score[c] for c in COUNTRIES], p_adjust="bonferroni")
            dunn.index = COUNTRIES
            dunn.columns = COUNTRIES
            log("\n" + dunn.to_string())
