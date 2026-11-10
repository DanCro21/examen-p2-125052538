"""API (Flask) - CRUD sobre la tabla de resultados del job MapReduce.

Pregunta: ingreso total por HORA DEL DIA (0-23) y CATEGORIA.
Clave del recurso: hora  (opcionalmente hora + categoria).

  GET    /resultados                       todos los registros
  GET    /resultados/<hora>                todas las categorias de esa hora
  GET    /resultados/<hora>/<categoria>    un registro
  POST   /resultados                       crear   {hora, categoria, total_ingresos, num_ventas}
  PUT    /resultados/<hora>/<categoria>    actualizar {total_ingresos, num_ventas}
  DELETE /resultados/<hora>/<categoria>    borrar
"""
import os
import time

import psycopg2
import psycopg2.errors
import psycopg2.extras
from flask import Flask, jsonify, request

app = Flask(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS resultados_hora_categoria (
    hora           SMALLINT NOT NULL CHECK (hora BETWEEN 0 AND 23),
    categoria      TEXT NOT NULL,
    total_ingresos NUMERIC(18,2) NOT NULL,
    num_ventas     BIGINT NOT NULL,
    PRIMARY KEY (hora, categoria)
)
"""


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def init_db(reintentos=30):
    for _ in range(reintentos):
        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(DDL)
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise RuntimeError("No se pudo conectar a la base de datos")


def query(sql, params=(), fetch="all"):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        if fetch == "all":
            return cur.fetchall()
        if fetch == "one":
            return cur.fetchone()
        return cur.rowcount


def serializar(fila):
    return {**fila, "total_ingresos": float(fila["total_ingresos"])}


def hora_valida(h):
    return isinstance(h, int) and 0 <= h <= 23


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/resultados")
def listar():
    filas = query("SELECT * FROM resultados_hora_categoria ORDER BY hora, categoria")
    return jsonify([serializar(f) for f in filas])


@app.get("/resultados/<int:hora>")
def por_hora(hora):
    if not hora_valida(hora):
        return jsonify(error="la hora debe estar entre 0 y 23"), 400
    filas = query(
        "SELECT * FROM resultados_hora_categoria WHERE hora = %s ORDER BY categoria", (hora,)
    )
    if not filas:
        return jsonify(error="no encontrado"), 404
    return jsonify([serializar(f) for f in filas])


@app.get("/resultados/<int:hora>/<categoria>")
def obtener(hora, categoria):
    fila = query(
        "SELECT * FROM resultados_hora_categoria WHERE hora=%s AND categoria=%s",
        (hora, categoria), "one",
    )
    if not fila:
        return jsonify(error="no encontrado"), 404
    return jsonify(serializar(fila))


@app.post("/resultados")
def crear():
    d = request.get_json(silent=True) or {}
    try:
        hora = int(d["hora"])
        categoria = str(d["categoria"]).strip()
        total = float(d["total_ingresos"])
        ventas = int(d["num_ventas"])
        if not categoria or not hora_valida(hora):
            raise ValueError
    except (KeyError, ValueError, TypeError):
        return jsonify(error="se requiere hora (0-23), categoria, total_ingresos, num_ventas"), 400
    try:
        query(
            "INSERT INTO resultados_hora_categoria (hora, categoria, total_ingresos, num_ventas) "
            "VALUES (%s,%s,%s,%s)",
            (hora, categoria, total, ventas), "none",
        )
    except psycopg2.errors.UniqueViolation:
        return jsonify(error="ya existe esa hora/categoria"), 409
    return jsonify(hora=hora, categoria=categoria, total_ingresos=total, num_ventas=ventas), 201


@app.put("/resultados/<int:hora>/<categoria>")
def actualizar(hora, categoria):
    d = request.get_json(silent=True) or {}
    try:
        total = float(d["total_ingresos"])
        ventas = int(d["num_ventas"])
    except (KeyError, ValueError, TypeError):
        return jsonify(error="se requiere total_ingresos y num_ventas"), 400
    n = query(
        "UPDATE resultados_hora_categoria SET total_ingresos=%s, num_ventas=%s "
        "WHERE hora=%s AND categoria=%s",
        (total, ventas, hora, categoria), "none",
    )
    if n == 0:
        return jsonify(error="no encontrado"), 404
    return jsonify(hora=hora, categoria=categoria, total_ingresos=total, num_ventas=ventas)


@app.delete("/resultados/<int:hora>/<categoria>")
def borrar(hora, categoria):
    n = query(
        "DELETE FROM resultados_hora_categoria WHERE hora=%s AND categoria=%s",
        (hora, categoria), "none",
    )
    if n == 0:
        return jsonify(error="no encontrado"), 404
    return "", 204


init_db()
