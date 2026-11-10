#!/usr/bin/env python3
"""Version secuencial (lectura linea a linea) de la MISMA pregunta que el MapReduce:
ingreso total por hora del dia (0-23) y categoria.

Uso: python3 secuencial.py <ruta_csv> [<salida.tsv>]
Escribe el resultado con el mismo formato que el reducer (hora, categoria, total,
num_ventas), ordenado por clave, para compararlo con `diff`. Imprime el tiempo en stderr.
"""
import sys
import time


def main():
    ruta = sys.argv[1]
    salida = sys.argv[2] if len(sys.argv) > 2 else None

    t0 = time.perf_counter()
    acum = {}          # (hora, categoria) -> [centavos, ventas]
    invalidas = 0
    with open(ruta, "r", encoding="utf-8", newline="") as f:
        for raw in f:
            linea = raw.strip()
            if not linea:
                continue
            partes = linea.split(",")
            if partes[0] == "id":
                continue
            if len(partes) != 8:
                invalidas += 1
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
                invalidas += 1
                continue
            a = acum.setdefault((hora, categoria), [0, 0])
            a[0] += cantidad * centavos
            a[1] += 1

    lineas = [
        f"{h}\t{c}\t{v[0] // 100}.{v[0] % 100:02d}\t{v[1]}\n"
        for (h, c), v in sorted(acum.items())
    ]
    if salida:
        with open(salida, "w", encoding="utf-8") as out:
            out.writelines(lineas)
    else:
        sys.stdout.writelines(lineas)

    sys.stderr.write(f"[secuencial] lineas invalidas: {invalidas} | tiempo: {time.perf_counter() - t0:.2f} s\n")


if __name__ == "__main__":
    main()
