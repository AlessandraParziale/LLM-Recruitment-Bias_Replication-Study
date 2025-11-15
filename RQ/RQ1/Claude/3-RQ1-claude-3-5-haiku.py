import json
import os
import anthropic
import pandas as pd

class Claude:
    def __init__(self, token):
        self.client = anthropic.Anthropic(api_key=token)

    def chat_completion(self, messages, model="claude-3-5-haiku-20241022"):
        system_prompt = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system_prompt += m["content"] + "\n"
            elif m["role"] == "user":
                user_messages.append(m["content"])
            elif m["role"] == "assistant":
                user_messages.append(m["content"]) 

        response = self.client.messages.create(
            model=model,
            max_tokens=1000,
            temperature=1,
            system=system_prompt.strip(),
            messages=[{"role": "user", "content": "\n".join(user_messages)}]
        )

        return response.content[0].text if response.content else "Error: No response"

    def conversation(self, prompt, history, model="claude-3-5-haiku-20241022"):
        history.append({"role": "user", "content": prompt})
        reply = self.chat_completion(history, model)
        history.append({"role": "assistant", "content": reply})
        return history

class Recruiter(Claude):
    def __init__(self, token, output_dir):
        super().__init__(token)
        self.output_dir = output_dir

    def init_csv(self):
        path = os.path.join(self.output_dir, "claude-3-5-haiku_results.csv")
        os.makedirs(self.output_dir, exist_ok=True)
        pd.DataFrame(columns=["Candidate list", "Recruit", "login"]).to_csv(path, index=False)

    def run(self, run_idx):
        df = pd.read_csv(f"./code/replication/dataset_extraction/dataset_{run_idx+1:03d}.csv")
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
        path = os.path.join(self.output_dir, "claude-3-5-haiku_results.csv")
        pd.DataFrame([row]).to_csv(path, mode='a', header=False, index=False)


def execute(token, repeats=10):
    base_path = "./code/replication/RQ/recruit-results/Claude"
    for rep in range(1, repeats+1):
        output_dir = os.path.join(base_path, f"run_{rep:02d}")
        rec = Recruiter(token, output_dir)
        rec.init_csv()
        for i in range(100):
            try:
                rec.run(i)
                print(f"Run {rep}, dataset {i+1}/100 done")
            except Exception as e:
                print(f"Error on run {rep}, dataset {i+1}: {e}")

if __name__ == "__main__":
    cfg_path = './code/config.json'
    cfg = json.load(open(cfg_path, 'r')) if os.path.exists(cfg_path) else {}
    token = cfg.get('CLAUDE_TOKEN') or os.getenv('CLAUDE_TOKEN')
    execute(token, repeats=10)
