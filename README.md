# Qualifying Offer Calculator

This lightweight script pulls the latest salary data from `https://questionnaire-148920.appspot.com/swe/data.html`, cleans any malformed rows, and computes the MLB qualifying offer (the average of the top 125 MLB salaries from the most recent season in the feed).

## Quickstart

1. **Install dependencies** (feel free to use a virtual environment):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the calculator**:
   ```bash
   python3 assignment_ques2.py
   ```

The script fetches the data live on each run and prints the detected season, the qualifying offer value, and a brief preview of the highest salaries used in the calculation. If the dataset changes or contains malformed values, those rows are skipped so they do not affect the final result.
# mlb-qualifying-offer-calculator
