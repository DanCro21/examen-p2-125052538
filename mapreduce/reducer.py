#!/usr/bin/env python3
"""Reducer (Hadoop Streaming). Recibe la entrada ORDENADA por clave.

Entrada : HH|categoria <TAB> centavos <TAB> 1
Salida  : hora <TAB> categoria <TAB> total_ingresos (2 decimales) <TAB> num_ventas
"""
import sys


def emitir(clave, centavos, ventas):
    hora, categoria = clave.split("|", 1)
    sys.stdout.write(f"{int(hora)}\t{categoria}\t{centavos // 100}.{centavos % 100:02d}\t{ventas}\n")


def main():
    actual = None
    centavos = 0
    ventas = 0
    for linea in sys.stdin:
        partes = linea.rstrip("\r\n").split("\t")
        if len(partes) != 3 or "|" not in partes[0]:
            continue
        clave = partes[0]
        try:
            c, n = int(partes[1]), int(partes[2])
        except ValueError:
            continue
        if clave != actual:
            if actual is not None:
                emitir(actual, centavos, ventas)
            actual, centavos, ventas = clave, 0, 0
        centavos += c
        ventas += n
    if actual is not None:
        emitir(actual, centavos, ventas)


if __name__ == "__main__":
    main()
