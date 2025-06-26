import csv
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set
from xml.etree.ElementTree import ElementTree

import requests

METAL_CODE = "1"  # Код золота в API ЦБ
CSV_HEADERS = ['Тикер', 'Сторона', 'Кол-во', 'Цена', 'Время', 'Название', 'Объем']

BASE_DIR = Path(__file__).parent.resolve()
RATES_DIR = BASE_DIR / "rates" / "metal"
LOGS_DIR = BASE_DIR / "logs"
RATES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

session_started: Set[Path] = set()


def fetch_metal_rates(min_date: datetime, max_date: datetime) -> ElementTree:
    date_from = (min_date - timedelta(days=3)).strftime("%d.%m.%Y")
    date_to = max_date.strftime("%d.%m.%Y")
    file_name = f"{date_from.replace('.', '_')}_to_{date_to.replace('.', '_')}.xml"
    path = RATES_DIR / file_name

    if not path.exists():
        url = (
            "https://www.cbr.ru/scripts/xml_metall.asp"
            f"?date_req1={date_from}&date_req2={date_to}"
        )
        print(f"[INFO] Загружаем курсы золота с {date_from} по {date_to}")
        resp = requests.get(url)
        resp.encoding = "windows-1251"
        resp.raise_for_status()
        path.write_text(resp.text, encoding="windows-1251")

    data = path.read_text(encoding="windows-1251")
    return ET.ElementTree(ET.fromstring(data))


def get_rate_for_date(tree: ET.ElementTree, target: datetime) -> float:
    root = tree.getroot()
    current = target

    while True:
        node_date = current.strftime("%d.%m.%Y")
        for rec in root.findall("Record"):
            if rec.get("Code") == METAL_CODE and rec.get("Date") == node_date:
                buy = rec.findtext("Buy", "").replace(",", ".")
                if buy:
                    return float(buy)
        current = current - timedelta(days=1)


# noinspection DuplicatedCode
def process_deal_row(row: Dict[str, str], run_dt: str, tree: ET.ElementTree) -> None:
    ticker: str = row['Тикер']
    side: str = row['Сторона']
    qty: int = int(float(row['Кол-во']))
    price: float = float(row['Цена'])
    deal_dt: datetime = datetime.strptime(row['Время'].split(",")[0].strip(), "%d.%m.%Y")
    t_minus_3: datetime = deal_dt - timedelta(days=3)
    rate: float = get_rate_for_date(tree, t_minus_3)
    total: float = round(qty * (price / 100) * rate, 2)

    log_file: Path = LOGS_DIR / f"{ticker}_GOLD.log"

    with open(log_file, "a", encoding="utf-8") as f:
        if log_file not in session_started:
            f.write(f"# Время запуска скрипта: {run_dt}\n")
            f.write(
                f"{'Дата сделки':10} | {'сторона':6} | {'кол-во':5} | "
                f"{'номинал':10} | {'курс':10} | {'сумма':12}\n"
            )
            session_started.add(log_file)

        f.write(
            f"{deal_dt.strftime('%d.%m.%Y'):10} | "
            f"{side:<6} | "
            f"{qty:>5} | "
            f"{price:10.4f} | "
            f"{rate:10.4f} | "
            f"{total:12.2f}\n"
        )

    print(f"{ticker}: {side} {qty}×{price} @ {rate} → {total}₽")


# noinspection DuplicatedCode
def parse_multiline_input() -> List[str]:
    print("Вставьте CSV-строки (Enter дважды — конец):")
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
    print("Обрабатываем золото (GOLD), лог → logs/metal/<тикер>_GOLD.log")
    lines = parse_multiline_input()
    if not lines:
        print("Нет данных.")
        sys.exit(1)

    reader = csv.DictReader(lines, fieldnames=CSV_HEADERS, delimiter=';')
    next(reader, None)

    deals = list(reader)
    dates = [
        datetime.strptime(r['Время'].split(",")[0].strip(), "%d.%m.%Y")
        for r in deals
    ]
    tree = fetch_metal_rates(min(dates), max(dates))

    run_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for row in deals:
        try:
            process_deal_row(row, run_dt, tree)
        except Exception as e:
            print("Ошибка при обработке:", row, file=sys.stderr)
            print(e, file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
