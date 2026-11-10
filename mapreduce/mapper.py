#!/usr/bin/env python3
"""Mapper (Hadoop Streaming).

Pregunta de negocio: ¿Cual es el INGRESO TOTAL por HORA DEL DIA (0-23) y CATEGORIA?
    ingreso = cantidad * precio_unitario
    hora    = HH de fecha_hora ("YYYY-MM-DD HH:MM:SS")

Entrada : id,fecha_hora,tienda,categoria,producto,cantidad,precio_unitario,metodo_pago
Salida  : HH|categoria <TAB> ingreso_en_centavos <TAB> 1
          (la hora va con 2 digitos para que el orden de la clave sea el correcto)

- Ignora el encabezado.
- Las lineas mal formadas se descartan SIN truncar el job y se cuentan en el
  contador de Hadoop  ventas / lineas_invalidas.
- Se trabaja en centavos (enteros) para que la suma sea exacta y coincida con
  la version secuencial.
"""
import sys

N_COLUMNAS = 8


def invalida():
    sys.stderr.write("reporter:counter:ventas,lineas_invalidas,1\n")


def main():
    for raw in sys.stdin:
        linea = raw.strip()          # quita \r\n (el CSV usa CRLF)
        if not linea:
            continue
        partes = linea.split(",")
        if partes[0] == "id":        # encabezado
            continue
        if len(partes) != N_COLUMNAS:
            invalida()
            continue
        try:
            fecha = partes[1]
            if len(fecha) < 13 or fecha[10] != " ":
                raise ValueError
            hora = int(fecha[11:13])
            categoria = partes[3].strip().replace("\t", " ").replace("|", " ")
            cantidad = int(partes[5])
            centavos = int(round(float(partes[6]) * 100))
            if not 0 <= hora <= 23 or not categoria or cantidad <= 0 or centavos < 0:
                raise ValueError
        except ValueError:
            invalida()
            continue
        sys.stdout.write(f"{hora:02d}|{categoria}\t{cantidad * centavos}\t1\n")


if __name__ == "__main__":
    main()
