import re
from pathlib import Path
from collections import defaultdict

LOGS_DIR = Path(__file__).parent / "logs"
COMPLETE_FILE = LOGS_DIR / "COMPLETE.txt"

line_pattern = re.compile(r"^\d{2}\.\d{2}\.\d{4}\s+\|\s+(buy|sell)\s+\|\s+\d+\s+\|.+?\|\s+[\d.]+\s+\|\s+([\d.]+)")


def main():
    summary = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
    seen_lines = set()

    for log_file in LOGS_DIR.glob("*.log"):
        ticker = log_file.name.split("_")[0].strip()

        with open(log_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line or not re.match(r"^\d{2}\.\d{2}\.\d{4}", line):
                    continue

                if line in seen_lines:
                    continue
                seen_lines.add(line)

                match = line_pattern.match(line)
                if match:
                    side, amount_str = match.groups()
                    amount = float(amount_str)
                    summary[ticker][side] += amount

    output_lines = [f"{'Тикер':10} | {'Sell':12} | {'Buy':12}", "-" * 10 + "-+-" + "-" * 12 + "-+-" + "-" * 12]

    for ticker in sorted(summary):
        buy = f"{summary[ticker]['buy']:.2f}"
        sell = f"{summary[ticker]['sell']:.2f}"
        output_lines.append(f"{ticker:<10} | {sell:>12} | {buy:>12}")

    COMPLETE_FILE.write_text("\n".join(output_lines), encoding="utf-8")

    print(f"[✓] Сводка записана в:\n → {COMPLETE_FILE}")


if __name__ == "__main__":
    main()
