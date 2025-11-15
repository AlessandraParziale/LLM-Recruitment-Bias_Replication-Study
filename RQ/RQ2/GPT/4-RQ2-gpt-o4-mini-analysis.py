import csv
import re
import pandas as pd
from collections import defaultdict, Counter

countries = ['US', 'BR', 'IN', 'UK', 'NG']

def import_response(path):
    with open(path, newline='') as f:
        return [row["Recruit"] for row in csv.DictReader(f)]

def divide(data):
    out = []
    for cell in data:
        for line in cell.splitlines():
            if not line.strip(): continue
            user, role = line.split(",", 1) if "," in line else (line, None)
            out.append([user.strip(), role.strip() if role else None])
    return out

def normalization_login(s):
    s = re.sub(r'^\d+\.\s*', '', s)
    return s.strip('><"')

def normalization_role(r):
    r = r.lower().strip('><" ,')
    r = r.replace('-', '').replace('fullstack', 'full stack')
    return r.replace('quality assurance', 'qa')

df_users = pd.concat([
    pd.read_csv(f"./code/replication/dataset_extraction/dataset_{i:03d}.csv")
    for i in range(1, 101)
], ignore_index=True)

raw = import_response("./code/replication/RQ/recruit-results/GPT/all-results/combined_results_fixed.csv")
pairs = divide(raw)
counter = defaultdict(Counter)

for login, role in pairs:
    if not role: 
        continue
    login_n = normalization_login(login)
    match = df_users.loc[df_users['login']==login_n, 'country']
    if match.empty:
        continue
    country = match.iloc[0]
    counter[normalization_role(role)][country] += 1


df = pd.DataFrame.from_dict(counter, orient='index').fillna(0)
df['total'] = df.sum(axis=1)
df = df[df['total'] >= 10].drop(columns='total')
df = df.div(df.sum(axis=1), axis=0).mul(100).reindex(columns=countries).fillna(0)
df = df.round(3)

print("[Result for RQ2]")
print(df)

output_path = "./code/replication/RQ/RQ2/GPT/results_gpt-o4-mini_RQ2.txt"

with open(output_path, "w", encoding="utf-8") as f:
    f.write("[Result for RQ2]\n")
    f.write(df.to_string())           
    f.write("\n\n")                   

print(f"Results: {output_path}")
