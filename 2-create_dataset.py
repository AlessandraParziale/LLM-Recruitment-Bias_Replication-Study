import os
import re
import pandas as pd
import pycountry
from langdetect import detect, DetectorFactory
from geotext import GeoText
import spacy

nlp = spacy.load("en_core_web_sm")

COUNTRY_CODES = {
    'US': 'United States',
    'BR': 'Brazil',
    'IN': 'India',
    'UK': 'United Kingdom',
    'NG': 'Nigeria',
}

DATASET_DIR = "./code/replication/dataset_extraction"
os.makedirs(DATASET_DIR, exist_ok=True)

DetectorFactory.seed = 0


def csv_to_df(path):
    return pd.read_csv(path)

def remove_duplicates(df):
    return df.drop_duplicates(subset='login', keep='first')

def detect_country_code(location_str):
    if not isinstance(location_str, str):
        return None
    gt = GeoText(location_str)
    for country_name in gt.country_mentions:
        for code, full in COUNTRY_CODES.items():
            if country_name.lower() == full.lower():
                return code
    loc_lower = location_str.lower()
    for code, full in COUNTRY_CODES.items():
        if full.lower() in loc_lower:
            return code
    return None

def preprocess_locations(df):
    df['country'] = df['location'].apply(detect_country_code)
    return df.dropna(subset=['country'])

def remove_newline(df):
    df['bio'] = df['bio'].str.replace(r'[\r\n]+', ' ', regex=True)
    df['location'] = df['location'].str.replace(r'[\r\n]+', ' ', regex=True)
    return df

def remove_non_bio(df):
    return df[df['bio'].notnull()]

def remove_location_in_bio(df):
    all_countries = [c.name for c in pycountry.countries]
    all_subs = [s.name for s in pycountry.subdivisions]
    mask = ~df['bio'].str.lower().isin([x.lower() for x in all_countries + all_subs])
    return df[mask]

def is_english(text):
    try:
        return detect(text) == 'en'
    except:
        return False

def remove_non_english(df):
    return df[df['bio'].apply(is_english)]


def tokenize_lengths(df):
    return [len(nlp(text)) for text in df['bio']]

def filter_bio_length(df, mean, std):
    df['bio_len'] = df['bio'].apply(lambda x: len(nlp(x)))
    lower, upper = mean - std/2, mean + std/2
    return df[(df['bio_len'] >= lower) & (df['bio_len'] <= upper)]\
             .drop(columns=['bio_len'])

def randomize(df):
    return df.sample(frac=1).reset_index(drop=True)


def make_slices(df, idx):
    n = len(df)
    i1 = (idx*2) % n
    i2 = (idx*2 + 1) % n
    return df.iloc[[i1, i2]]




# --- MAIN ---
if __name__ == "__main__":

    files = [
        "./code/replication/github-profile/githubprofile_2021-01.csv",
        "./code/replication/github-profile/githubprofile_2022-01.csv",
        "./code/replication/github-profile/githubprofile_2023-01.csv",
        "./code/replication/github-profile/githubprofile_2024-01.csv",
        "./code/replication/github-profile/githubprofile_2025-01.csv"
    ]

    df = pd.concat([csv_to_df(f) for f in files], ignore_index=True)

    df = df.drop(columns=['pronouns'], errors='ignore')

    df = remove_duplicates(df)
    df = remove_newline(df)
    df = preprocess_locations(df)
    df = remove_non_bio(df)
    df = remove_location_in_bio(df)
    df = remove_non_english(df)

    all_lens = tokenize_lengths(df)
    mean_len = pd.Series(all_lens).mean()
    std_len  = pd.Series(all_lens).std(ddof=0)
    df = filter_bio_length(df, mean_len, std_len)

    dfs_by_country = {
        code: randomize(df[df['country'] == code])
        for code in COUNTRY_CODES
    }

    # 100 files from 18 profiles (2 per country)
    master_out = []
    for i in range(100):
        group_num = i + 1
        out = []
        for code in COUNTRY_CODES:
            dfc = dfs_by_country[code]
            out.append(make_slices(dfc, i))
        df_out = pd.concat(out, ignore_index=True)
        df_out = randomize(df_out)
        df_out = df_out.reset_index(drop=True)

        master_out.append(df_out)
        path = os.path.join(DATASET_DIR, f"dataset_{group_num:03d}.csv")
        df_out.to_csv(path, index=False)
        print(f"Saved {path} ({len(df_out)} profili)")

    master_df = pd.concat(master_out, ignore_index=True)
    agg_path = os.path.join(DATASET_DIR, "dataset_all_groups.csv")
    master_df.to_csv(agg_path, index=False)
