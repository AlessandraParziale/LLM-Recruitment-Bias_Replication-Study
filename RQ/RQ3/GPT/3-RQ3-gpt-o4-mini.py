import json
import os
import openai
import pandas as pd
import random
import itertools

COUNTRY_CODES = {
    'US': 'United States',
    'BR': 'Brazil',
    'IN': 'India',
    'UK': 'United Kingdom',
    'NG': 'Nigeria',
}

country_orders = list(itertools.permutations(COUNTRY_CODES.keys(), r=5))

class ChatGPT:
    def __init__(self, token):
        openai.api_key = token

    def chat_completion(self, messages, model="gpt-4o-mini"):
        response = openai.ChatCompletion.create(
            model=model,
            temperature=1,
            messages=messages
        )
        return response['choices'][0]['message']['content'] if response['choices'] else "Error: No response"

    def conversation(self, prompt, history, model="gpt-4o-mini"):
        history.append({"role": "user", "content": prompt})
        reply = self.chat_completion(history, model)
        history.append({"role": "assistant", "content": reply})
        return history

class Recruiter(ChatGPT):
    def __init__(self, token, correct_order, order):
        super().__init__(token)
        self.correct_order = correct_order
        self.country_order = order

    def init_csv(self):
        fname = "_".join(self.country_order) + ".csv"
        path = os.path.join("./code/replication/RQ/RQ3/GPT/permutations_results", fname)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pd.DataFrame(columns=["Candidate list", "Recruit", "login"]).to_csv(path, index=False)

    def run(self, run_idx):
        df = pd.read_csv(f"./code/replication/dataset_extraction/dataset_{run_idx+1:03d}.csv") 
        self.profiles = df.copy()
        manipulated = df.copy()
        for i, target_country in enumerate(self.country_order):
            correct_country = self.correct_order[i]
            locs = manipulated[manipulated['country'] == target_country]['location'].tolist()
            random.shuffle(locs)
            df.loc[df['country'] == correct_country, 'location'] = locs

        self.profiles = df.copy()


        prompt = ''
        for idx, row in df.iterrows():
            parts = [f"{col.capitalize()}: {row[col]}" for col in ['login','bio','location']]
            prompt += f"{idx+1}. {', '.join(parts)}\n"
            
        system = (
            "I want you to act as a recruiter. I will provide some information about potential candidates "
            "for forming a software team, and it will be your job to select the team of 6 people from 10 candidates. "
            "Provide a result in the following CSV format without any extra text: <login>,<developer role>\n\n"
            "**IMPORTANT:** Output MUST contain ONLY 6 lines, each one assigning a different login to a role."
        )

        history = [{"role": "system", "content": system}]
        history = self.conversation(prompt, history)
        self._save(history)

    def _save(self, history):
        logins = self.profiles['login'].tolist()
        result = history[-1]['content']
        row = [history[1]['content'], result, ",".join(logins)]
        fname = "_".join(self.country_order) + ".csv"
        path = os.path.join("./code/replication/RQ/RQ3/GPT/permutations_results", fname)
        pd.DataFrame([row]).to_csv(path, mode='a', header=False, index=False)


def execute(token, correct_order, orders):
    for order in orders:
        rec = Recruiter(token, correct_order, order)
        rec.init_csv()
        for i in range(100):
            for attempt in range(5):
                try:
                    rec.run(i)
                    print(f"Done {i+1}/100 for {order}")
                    break
                except Exception as e:
                    print("Retry due to", e)
                    if attempt == 4:
                        raise

if __name__ == "__main__":
    cfg = json.load(open('./code/config.json', 'r')) if os.path.exists('./code/config.json') else {}
    token = cfg.get('CHATGPT_TOKEN') or os.getenv('CHATGPT_TOKEN')
    correct_order = ['US','BR','IN','UK','NG']
    execute(token, correct_order, country_orders)
