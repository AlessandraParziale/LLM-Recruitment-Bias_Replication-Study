import csv
import json
import os
from datetime import datetime, timedelta
import time
import requests

class GitHubAPI:
    def __init__(self, token):
        self.token = token
    
    def execute_graphql(self, query, try_count=5):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        for _ in range(try_count):
            response = requests.post("https://api.github.com/graphql", json={"query": query}, headers=headers)
            
            if response.status_code == 200:
                return json.loads(response.text)
            elif response.status_code == 502:
                print("API rate limit exceeded. Retrying in 30 seconds...")
                time.sleep(30)
        raise Exception("Failed to run query: ", response.status_code, response.text)

class GitHubProfileScraper:
    def __init__(self, period, token, init_csv=False):
        self.period = period
        self.token = token
        self.githubapi = GitHubAPI(self.token)
        self.csv_file_name = f"./code/replication/github-profile/githubprofile_{self.period}.csv"
        if init_csv:
            self.init_csv(["login", "location", "bio", "createdAt"])

    def make_query(self, start_date, end_date, after_cursor=None):
        cursor_part = f', after: "{after_cursor}"' if after_cursor else ''
        return f'''
        {{
            search(query: "created:{start_date}..{end_date} type:user", type: USER, first: 100{cursor_part}) {{
                pageInfo {{
                    endCursor
                    hasNextPage
                }}
                edges {{
                    node {{
                        ... on User {{
                            login
                            location
                            bio
                            createdAt
                        }}
                    }}
                }}
            }}
        }}
        '''

    def timerange(self, delta=timedelta(minutes=9, seconds=59)):
        start_datetime = datetime.strptime(f"{self.period}-01T00:00:00", "%Y-%m-%dT%H:%M:%S")
        end_datetime = datetime.strptime(f"{self.period}-31T23:59:59", "%Y-%m-%dT%H:%M:%S")
        current_datetime = start_datetime
        while current_datetime < end_datetime:
            next_datetime = current_datetime + delta
            yield current_datetime, min(next_datetime, end_datetime)
            current_datetime = next_datetime + timedelta(seconds=1)

    def init_csv(self, column_names):
        os.makedirs(os.path.dirname(self.csv_file_name), exist_ok=True)
        with open(self.csv_file_name, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(column_names)

    def delay_until_reset(self):
        target_time_str = self.githubapi.execute_graphql(self.check_ratelimit_query())["data"]["rateLimit"]["resetAt"]
        target_time = datetime.strptime(target_time_str, "%Y-%m-%dT%H:%M:%SZ")
        now = datetime.utcnow()
        delta = int((target_time - now).total_seconds()) + 60
        print(f"API rate limit exceeded. Retrying at {target_time} UTC")
        minutes, seconds = divmod(delta, 60)
        print(f"Sleeping for {minutes} minutes {seconds} seconds")
        time.sleep(delta)

    def fetch_and_save_data(self):
        all_data = []
        for from_datetime, to_datetime in self.timerange():
            from_str = from_datetime.strftime("%Y-%m-%dT%H:%M:%S")
            to_str = to_datetime.strftime("%Y-%m-%dT%H:%M:%S")
            print(f"Fetching data from {from_str} to {to_str}")
            has_next_page = True
            after_cursor = None
            batch = []

            while has_next_page:
                query = self.make_query(from_str, to_str, after_cursor)
                result = self.githubapi.execute_graphql(query)
                if 'data' not in result:
                    self.delay_until_reset()
                    result = self.githubapi.execute_graphql(query)

                for edge in result['data']['search']['edges']:
                    node = edge['node']
                    login      = node.get('login')
                    location   = node.get('location')
                    bio        = node.get('bio')
                    created_at = node.get('createdAt')

                    if all(field not in (None, "") for field in (login, location, bio, created_at)):
                        batch.append([login, location, bio, created_at])

                pageInfo = result['data']['search']['pageInfo']
                has_next_page = pageInfo['hasNextPage']
                after_cursor = pageInfo['endCursor']

            if len(batch) == 1000:
                raise Exception("Error: Too many records in one interval.")

            all_data.extend(batch)

            if to_str.endswith("23:59:59"):
                with open(self.csv_file_name, "a", newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows(all_data)
                print(f"Saved {len(all_data)} rows to {self.csv_file_name}")
                all_data = []

        print("Finished scraping all periods.")

    def check_ratelimit_query(self):
        return '''
        query {
            rateLimit {
                limit
                cost
                remaining
                resetAt
            }
        }
        '''



# --- MAIN ---
if __name__ == "__main__":
    config = {}
    if os.path.exists("./code/config.json"):
        with open("./code/config.json", "r") as f:
            config = json.load(f)
    GITHUB_TOKEN = config.get("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")

    periods = ["2021-01", "2022-01", "2023-01", "2024-01", "2025-01"]
    for period in periods:
        scraper = GitHubProfileScraper(period=period, token=GITHUB_TOKEN, init_csv=True)
        scraper.fetch_and_save_data()
