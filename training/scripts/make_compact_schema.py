#!/usr/bin/env python3
"""Build a compact tool schema + system prompt for 1024-token training."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

DESCRIPTIONS = {
    "battery_status": "Заряд батареи и состояние (заряжается/разряжается).",
    "wifi_status": "Показать активную Wi-Fi сеть и сохранённые сети. Не подключает.",
    "wifi_connect": "Подключиться к сохранённой Wi-Fi сети по имени.",
    "services_running": "Список запущенных системных сервисов.",
    "service_logs": "Последние строки журнала сервиса из списка.",
    "service_restart": "Перезапустить сервис из списка.",
    "nosleep_set": "Запретить сон (on) или разрешить (off).",
    "volume_get": "Текущая громкость и выключен ли звук.",
    "volume_set": "Установить громкость 0–100.",
    "volume_step": "Сделать громче или тише на шаг.",
    "mute_set": "Заглушить (on) или вернуть звук (off).",
    "brightness_set": "Установить яркость экрана 5–100.",
    "brightness_step": "Сделать экран ярче или темнее на шаг.",
}

PARAMS = {
    "wifi_connect": {"connection": "имя сохранённой сети"},
    "service_logs": {"unit": "сервис из списка", "lines": "строк, 1–200"},
    "service_restart": {"unit": "сервис из списка"},
    "nosleep_set": {"mode": "on — запретить сон, off — разрешить"},
    "volume_set": {"percent": "0–100"},
    "volume_step": {"direction": "up — громче, down — тише"},
    "mute_set": {"mode": "on — заглушить, off — вернуть звук"},
    "brightness_set": {"percent": "5–100"},
    "brightness_step": {"direction": "up — ярче, down — темнее"},
}

SYSTEM = (
    "Ты Кузя, офлайн-агент skladenOS. Работай только через инструменты и не вызывай "
    "инструмент, если просьба не совпадает с его описанием. Умеешь: заряд батареи; "
    "статус Wi-Fi и подключение к сохранённой сети; список сервисов; журнал и перезапуск "
    "семи сервисов; запрет/разрешение сна; громкость, mute, шаг громкости; яркость и шаг "
    "яркости. Не умеешь: включать/выключать Wi-Fi, останавливать службы, ssh/sshd, файлы, "
    "диск, звонки, будильник, фонарик, браузер, перевод, вычисления, питание телефона. "
    "Остальное — ответь текстом. «Остановить» не равно «перезапустить»; «все службы» — "
    "не одна служба. mute on — выключить звук, off — вернуть; nosleep on — запретить сон, "
    "off — разрешить."
)


def main() -> None:
    full = json.loads((DATA / "tools-schema.json").read_text())
    out = []
    for item in full:
        fn = item["function"]
        name = fn["name"]
        params = fn.get("parameters", {})
        props = params.get("properties", {})
        short_props = {}
        for key, schema in props.items():
            new = dict(schema)
            if name in PARAMS and key in PARAMS[name]:
                new["description"] = PARAMS[name][key]
            short_props[key] = new
        params["properties"] = short_props
        fn["description"] = DESCRIPTIONS.get(name, fn["description"])
        out.append(item)
    (DATA / "tools-schema-compact.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    )
    (DATA / "system-prompt-compact.txt").write_text(SYSTEM + "\n")
    print("wrote compact schema and system prompt")


if __name__ == "__main__":
    main()
