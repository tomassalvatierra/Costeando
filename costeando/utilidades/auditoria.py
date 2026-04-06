import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _normalizar_valor_json(valor: Any) -> Any:
    if isinstance(valor, (str, int, float, bool)) or valor is None:
        return valor
    if isinstance(valor, list):
        return [_normalizar_valor_json(item) for item in valor]
    if isinstance(valor, dict):
        return {str(k): _normalizar_valor_json(v) for k, v in valor.items()}
    return str(valor)


def guardar_manifiesto_ejecucion(
    carpeta_guardado: str,
    id_ejecucion: str,
    proceso: str,
    estado: str,
    entradas: dict[str, Any],
    parametros: dict[str, Any],
    metricas: dict[str, Any],
    archivos_generados: dict[str, str],
    codigo_error: str | None = None,
):
    carpeta = Path(carpeta_guardado)
    carpeta.mkdir(parents=True, exist_ok=True)

    manifiesto = {
        "id_ejecucion": id_ejecucion,
        "proceso": proceso,
        "estado": estado,
        "fecha_hora": datetime.now().isoformat(timespec="seconds"),
        "entradas": _normalizar_valor_json(entradas),
        "parametros": _normalizar_valor_json(parametros),
        "metricas": _normalizar_valor_json(metricas),
        "archivos_generados": _normalizar_valor_json(archivos_generados),
        "codigo_error": codigo_error,
    }
    path_manifiesto = carpeta / f"{datetime.now().strftime('%Y-%m-%d')}_manifiesto_{proceso}_{id_ejecucion}.json"
    with open(path_manifiesto, "w", encoding="utf-8") as archivo:
        json.dump(manifiesto, archivo, ensure_ascii=True, indent=2)
    logger.info("Manifiesto de auditoria guardado en: %s", os.fspath(path_manifiesto))
    return os.fspath(path_manifiesto)
