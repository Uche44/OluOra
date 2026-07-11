import re
import sys

# Configure stdout to handle all unicode characters safely
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

transcript_path = r"C:\Users\HP\.gemini\antigravity-ide\brain\747e41e1-e763-4d9c-8e30-b3517bb34773\.system_generated\logs\transcript.jsonl"

try:
    with open(transcript_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            matches = re.findall(r"Milestone \d+\b", line, re.IGNORECASE)
            if matches:
                # filter unique matches that we want to see (e.g. 9, 10, 11, etc.)
                found_interesting = False
                for m in matches:
                    num = int(m.split()[1])
                    if 9 <= num <= 17:
                        found_interesting = True
                
                if found_interesting:
                    idx = line.find(matches[0])
                    start = max(0, idx - 50)
                    end = min(len(line), idx + 250)
                    snippet = line[start:end]
                    print(f"Line {i} (Match {matches[0]}): ... {snippet} ...")
except Exception as e:
    print(f"Error reading transcript: {e}")
