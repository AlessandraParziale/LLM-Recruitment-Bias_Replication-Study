# Online Appendix – Repository Structure and Contents

This repository contains all materials used to conduct the replication and extension study on **GitHub Profile Recruitment Bias in Large Language Models**.  
It includes datasets, sampling procedures, scripts, and raw outputs for all research questions (RQ1–RQ3).  

---

## 📁 Repository Overview

### **1. `github-profile/`**
This folder contains the **full dataset of GitHub developer profiles**, collected annually from **January 2021 to January 2025**.  
Each yearly snapshot includes:
- Developer bio information  
- Profile metadata  
- Publicly available attributes used in the study  

These datasets constitute the base population from which samples were extracted for the experiments.

---

### **2. `dataset_extraction/`**
This folder contains the **100 groups of 10 developers** (for a total of 1,000 sampled profiles) used in the replication study.  
Each group was randomly sampled from the combined multi-year dataset and represents one independent evaluation unit in the study design.

---

### **3. `RQ/`**
This root folder includes one subfolder per research question:
- `RQ1/`
- `RQ2/`
- `RQ3/`
  
and a subfolder named `recruit-results/` that contains the raw recruitment decisions by the LLMs.


Each RQ folder contains **three subfolders**, corresponding to the three evaluated LLM families:
- `Claude/`
- `DeepSeek/`
- `GPT/`

Inside each LLM-specific folder you will find:
- **Python scripts** used to generate prompts, execute queries, and run evaluations  
- **Raw results** generated for each model
- **Post-processing scripts** for data cleaning or aggregating results (when applicable)

---


