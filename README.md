# JobSmart

Intelligent job search pipeline for the Canadian market.

Ingests job postings from 6 sources in real time, scores each role
against a personal profile using NLP, and presents a ranked dashboard
to prioritize applications.

## Tech stack
- Python 3.12
- MySQL 8.0
- Streamlit
- spaCy · scikit-learn · jobspy

## Setup
1. Clone the repo
2. conda activate jobsmart
3. pip install -r requirements.txt
4. Add your credentials to .env
5. make init
6. make run
7. make dashboard

## Live demo
Coming soon — deploying to Streamlit Cloud