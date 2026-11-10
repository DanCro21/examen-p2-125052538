#!/usr/bin/env python3
"""Lee la salida del job (part-00000) e inserta/actualiza la tabla resultados_hora_categoria.

Se ejecuta DENTRO del contenedor api (ya tiene red hacia db y el volumen de salida):
    docker compose exec api python scripts/cargar_resultados.py
"""
import os
import sys

import psycopg2

RESULT_FILE = os.environ.get("RESULT_FILE", "/data/output/resultado/part-00000")

DDL = """
CREATE TABLE IF NOT EXISTS resultados_hora_categoria (
    hora           SMALLINT NOT NULL CHECK (hora BETWEEN 0 AND 23),
    categoria      TEXT NOT NULL,
    total_ingresos NUMERIC(18,2) NOT NULL,
    num_ventas     BIGINT NOT NULL,
    PRIMARY KEY (hora, categoria)
)
"""

UPSERT = """
INSERT INTO resultados_hora_categoria (hora, categoria, total_ingresos, num_ventas)
VALUES (%s, %s, %s, %s)
ON CONFLICT (hora, categoria) DO UPDATE
SET total_ingresos = EXCLUDED.total_ingresos, num_ventas = EXCLUDED.num_ventas
"""


def leer(ruta):
    filas = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            partes = linea.rstrip("\r\n").split("\t")
            if len(partes) != 4:
                continue
            filas.append((int(partes[0]), partes[1], partes[2], int(partes[3])))
    return filas


def main():
    if not os.path.exists(RESULT_FILE):
        sys.exit(f"No existe {RESULT_FILE}. Ejecuta primero el job de MapReduce.")
    filas = leer(RESULT_FILE)
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )
    with conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.executemany(UPSERT, filas)
    conn.close()
    print(f"Cargados {len(filas)} registros desde {RESULT_FILE}")


if __name__ == "__main__":
    main()
