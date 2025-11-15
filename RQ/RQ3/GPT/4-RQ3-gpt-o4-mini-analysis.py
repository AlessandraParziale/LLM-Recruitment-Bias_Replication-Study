import csv
import ast
import itertools
import re
import os
from functools import lru_cache

import pandas as pd
from scipy import stats
import scikit_posthocs as sp

COUNTRY_CODES = {
    'US': 'United States',
    'BR': 'Brazil',
    'IN': 'India',
    'UK': 'United Kingdom',
    'NG': 'Nigeria',
}

countries = list(COUNTRY_CODES.keys())
country_orders = list(itertools.permutations(countries, len(countries)))
baseline = tuple(countries)


def normalize_login(login: str) -> str:
    return login.strip().lower()


def parse_login_field(raw):
    if not isinstance(raw, str):
        return []
    return [normalize_login(tok) for tok in raw.split(",") if tok.strip()]


def parse_recruit_field(raw):
    if not isinstance(raw, str):
        return []
    lines = re.split(r'[\r\n]+', raw.strip())
    logins = []
    for line in lines:
        parts = line.split(",", 1)
        if parts:
            login = parts[0].strip()
            if login:
                logins.append(normalize_login(login))
    return logins


def import_response(csv_file_path):
    out = []
    with open(csv_file_path, newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            raw = row.get("Recruit", "")
            recruits = parse_recruit_field(raw)
            out.append(recruits)
    return out


def import_login(path_csv):
    out = []
    with open(path_csv, newline='') as f:
        for row in csv.DictReader(f):
            raw = row.get("login", "")
            logins = parse_login_field(raw)
            out.append(logins)
    return out


def filter_six(recruits_list, login_id_list, required_matches=6):
    bad_indices = set()
    minlen = min(len(recruits_list), len(login_id_list))
    for i in range(minlen):
        if len(set(recruits_list[i]) & set(login_id_list[i])) != required_matches:
            bad_indices.add(i)
    for i in range(minlen, max(len(recruits_list), len(login_id_list))):
        bad_indices.add(i)
    return sorted(bad_indices)


@lru_cache(maxsize=None)
def load_dataset(index: int) -> pd.DataFrame:
    path = f"./code/replication/dataset_extraction/dataset_{index:03d}.csv"
    return pd.read_csv(path)


def make_score(recruits_list, login_id_list, countries, filter_i):
    score = {c: [] for c in countries}
    for i, logins in enumerate(login_id_list):
        if i in filter_i:
            continue
        if i >= len(recruits_list):
            continue
        try:
            df = load_dataset(i + 1)
        except FileNotFoundError:
            continue
        mapping = {
            str(l).strip().lower(): c for l, c in zip(df['login'], df['country'])
            if pd.notna(l) and pd.notna(c)
        }
        s = {c: 0 for c in countries}
        recruits = recruits_list[i]
        for login in logins:
            if login not in recruits:
                continue
            country = mapping.get(login)
            if country in countries:
                s[country] += 1
        for country in countries:
            score[country].append(s[country])
    return score


def main_rq3():
    output_dir = "./code/replication/RQ/RQ3/GPT"
    output_path = os.path.join(output_dir, "results_gpt-o4-mini_RQ3.txt")
    os.makedirs(output_dir, exist_ok=True)

    lines = []

    filter_i_set = set()
    for order in country_orders:
        path = f"./code/replication/RQ/RQ3/GPT/permutations_results/{'_'.join(order)}.csv"
        resp = import_response(path)
        logins = import_login(path)
        bad = filter_six(resp, logins)
        filter_i_set.update(bad)
    filter_i = sorted(filter_i_set)

    score = {source: {target: [] for target in countries if target != source} for source in countries}

    for order in country_orders:
        if order == baseline:
            continue
        path = f"./code/replication/RQ/RQ3/GPT/permutations_results/{'_'.join(order)}.csv"
        recruits = import_response(path)
        logins = import_login(path)
        tmp = make_score(recruits, logins, countries, filter_i)
        for idx, source_country in enumerate(countries):
            target_location = order[idx]
            if source_country == target_location:
                continue
            score[source_country][target_location].extend(tmp.get(source_country, []))


    header = "[Result for RQ3]"
    print(header)
    lines.append(header + "\n")
    for i in range(2, -1, -1):
        print(f"{i} candidate")
        lines.append(f"{i} candidate\n")
        for source_country in countries:
            print(f"[Bio-{source_country}]")
            lines.append(f"[Bio-{source_country}]\n")
            for target_location in countries:
                if source_country == target_location:
                    continue
                arr = score[source_country][target_location]
                pct = (arr.count(i) / len(arr) * 100) if arr else 0
                out = f"Location-{target_location}: {pct:.0f}%"
                print(out)
                lines.append(out + "\n")
        print()
        lines.append("\n")

    for source_country in countries:
        print(f"[{source_country}]")
        lines.append(f"[{source_country}]\n")

        print("Kruskal-Wallis test")
        lines.append("Kruskal-Wallis test\n")

        groups = []
        group_labels = []
        for target_location in countries:
            if source_country == target_location:
                continue
            arr = score[source_country][target_location]
            if arr:
                groups.append(arr)
                group_labels.append(target_location)

        if len(groups) < 2:
            print("Insufficient data for Kruskal-Wallis\n")
            lines.append("Insufficient data for Kruskal-Wallis\n\n")
            continue

        stat, pval = stats.kruskal(*groups)
        print(f"p = {pval}")
        lines.append(f"p = {pval}\n")

        if pval < 0.05:
            print("p < 0.05")
            lines.append("p < 0.05\n")

            print("Dunn's post-hoc (Bonferroni)")
            lines.append("Dunn's post-hoc (Bonferroni)\n")

            dm = sp.posthoc_dunn(groups, p_adjust="bonferroni")
            dm.index = group_labels
            dm.columns = group_labels

            dm_str = dm.to_string()
            print(dm_str)
            lines.append(dm_str + "\n")
        else:
            print("p >= 0.05")
            lines.append("p >= 0.05\n")

        print()
        lines.append("\n")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"Results have been written to the file: {output_path}")
    except Exception as e:
        print(f"Error writing the results file: {e}")


if __name__ == "__main__":
    main_rq3()
