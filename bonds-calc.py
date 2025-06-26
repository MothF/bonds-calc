import csv
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set

import requests

CURRENCY_URL = "https://www.cbr.ru/scripts/XML_daily.asp?date_req={}"
CSV_HEADERS = ['Тикер', 'Сторона', 'Кол-во', 'Цена', 'Время', 'Название', 'Объем']

BASE_DIR = Path(__file__).parent.resolve()
RATES_DIR = BASE_DIR / "rates" / "currency"
RATES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

session_started: Set[Path] = set()


def fetch_currency_rate(date_str: str, currency_code: str) -> float:
    xml_file = RATES_DIR / f"{date_str.replace('.', '_')}.xml"
    if not xml_file.exists():
        print(f"Запрос курсов по адресу {CURRENCY_URL.format(date_str)}")
        resp = requests.get(CURRENCY_URL.format(date_str))
        if resp.status_code != 200:
            raise RuntimeError(f"Не удалось получить курсы: HTTP {resp.status_code}")
        xml_file.write_text(resp.text, encoding="windows-1251")
    data = xml_file.read_text(encoding="windows-1251")
    root = ET.fromstring(data)
    for val in root.findall("Valute"):
        if val.findtext("CharCode") == currency_code:
            return round(float(val.findtext("Value", "0").replace(",", ".")), 6)
    raise SystemExit(f"Валюта '{currency_code}' не найдена в XML за {date_str}")


# noinspection DuplicatedCode
def process_deal_row(row: Dict[str, str], currency: str, run_dt: str) -> None:
    ticker: str = row['Тикер']
    side: str = row['Сторона']
    qty: int = int(float(row['Кол-во']))
    price: float = float(row['Цена'])
    deal_dt: datetime = datetime.strptime(row['Время'].split(",")[0].strip(), "%d.%m.%Y")
    t_minus_1: datetime = deal_dt - timedelta(days=1)
    rate: float = fetch_currency_rate(t_minus_1.strftime("%d.%m.%Y"), currency)
    total: float = round(qty * price * rate, 2)

    log_file: Path = LOGS_DIR / f"{ticker}_{currency}.log"

    with open(log_file, "a", encoding="utf-8") as f:
        if log_file not in session_started:
            f.write(f"# Время запуска скрипта: {run_dt}\n")
            f.write(
                f"{'Дата сделки':10} | {'сторона':6} | {'кол-во':5} | "
                f"{'номинал':10} | {'курс':10} | {'сумма':12}\n"
            )
            session_started.add(log_file)

        f.write(
            f"{deal_dt.strftime("%d.%m.%Y"):10} | "
            f"{side:<6} | "
            f"{qty:>5} | "
            f"{price:10.4f} | "
            f"{rate:10.4f} | "
            f"{total:12.2f}\n"
        )

    print(f"{ticker}: {side} {qty}×{price} {currency} @ {rate} → {total}₽")


# noinspection DuplicatedCode
def parse_multiline_input() -> List[str]:
    print("Вставьте CSV-строки (Enter дважды для окончания):")
    lines: List[str] = []
    while True:
        try:
            ln = input()
            if not ln.strip():
                break
            for part in ln.splitlines():
                if part.strip():
                    lines.append(part.strip())
        except EOFError:
            break
    return lines


def main() -> None:
    currency = input("Введите валюту (например, USD): ").strip().upper()
    lines = parse_multiline_input()
    if not lines:
        print("Нет данных для обработки.")
        sys.exit(1)

    run_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reader = csv.DictReader(lines, fieldnames=CSV_HEADERS, delimiter=';')
    next(reader)
    for row in reader:
        try:
            process_deal_row(row, currency, run_dt)
        except Exception as e:
            print("❌ Ошибка при обработке:", row, file=sys.stderr)
            print(e, file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
