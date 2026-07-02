import os
import pandas as pd
from datetime import datetime
from plyer import notification
from data_sources import load_historial, save_historial, get_current_snapshot

def send_mac_notification(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name='Venezuela Dashboard',
            timeout=10,
        )
    except Exception:
        pass

def check_for_updates():
    snapshot, _ = get_current_snapshot()
    historial = load_historial()

    if historial.empty:
        save_historial(pd.DataFrame([snapshot]))
        send_mac_notification(
            'Venezuela Dashboard',
            f"Panel iniciado: {snapshot.get('muertos', '?')} muertos, {snapshot.get('heridos', '?')} heridos"
        )
        return snapshot

    last = historial.iloc[-1]
    changes = []
    for col in ['muertos', 'heridos', 'desaparecidos']:
        old = last.get(col)
        new = snapshot.get(col)
        if old is not None and new is not None and new != old:
            diff = new - old
            sign = '+' if diff > 0 else ''
            changes.append(f"{col}: {sign}{diff} (de {old} a {new})")

    if changes:
        new_row = pd.DataFrame([snapshot])
        historial = pd.concat([historial, new_row], ignore_index=True)
        save_historial(historial)
        send_mac_notification(
            'Nuevo balance Venezuela',
            '\n'.join(changes)
        )
    else:
        save_historial(pd.concat([historial, pd.DataFrame([snapshot])], ignore_index=True))

    return snapshot
