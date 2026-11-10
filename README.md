# Examen Segundo Parcial – Pipeline de datos contenerizado

- **Matrícula:** 125052538
- **Dataset:** `ventas_125052538.csv` (5,000,000 filas, ~350 MB)
- **Pregunta asignada:** **Ingreso total por hora del día (0–23) y categoría** (`ingreso = cantidad × precio_unitario`; la hora sale de `fecha_hora`).
  - Clave del resultado: `hora` + `categoria` (24 horas × 10 categorías = 240 registros)
  - Salida: `hora <TAB> categoria <TAB> total_ingresos <TAB> num_ventas`


## Cómo reproducir

```bash
# 1. Variables de entorno (NO se versiona .env)
cp .env.example .env            

# 2. Coloca el dataset (ignorado por git)
cp /ruta/ventas_125052538.csv data/

# 3. Levantar todo
docker compose up -d --build

# 4. Parte A: hadoop version
docker compose exec -u hadoop hadoop hadoop version

# 5. Parte B: SSH sin contraseña
docker compose exec -u hadoop hadoop ssh -o BatchMode=yes localhost 'echo "ssh localhost OK: $(whoami)@$(hostname)"'     # dentro de hadoop
docker compose exec api ssh -o BatchMode=yes hadoop@hadoop 'echo "api -> hadoop OK: $(whoami)@$(hostname)"'             # de api -> hadoop

# 6. Parte C: job MapReduce (con tiempo)
docker compose exec -u hadoop hadoop bash -c '
  mkdir -p /tmp/job && cp /opt/mapreduce/*.py /tmp/job/ && cd /tmp/job
  rm -rf /data/output/resultado
  time hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
    -input /data/input/$DATASET_FILE \
    -output /data/output/resultado \
    -mapper "python3 mapper.py" -reducer "python3 reducer.py" \
    -file mapper.py -file reducer.py
  cat /data/output/resultado/part-00000'

# 7. Parte C2: version secuencial (con tiempo) y comparacion de resultados
docker compose exec -u hadoop hadoop bash -c '
  time python3 /opt/mapreduce/secuencial.py /data/input/$DATASET_FILE /data/output/secuencial.tsv
  diff /data/output/resultado/part-00000 /data/output/secuencial.tsv && echo "RESULTADOS COINCIDEN"'

# 8. Parte D: cargar a la BD y consultar la API
docker compose exec api python scripts/cargar_resultados.py
curl http://localhost:5000/resultados                    # todos (240)
curl http://localhost:5000/resultados/18                 # todas las categorias de las 18 h
curl http://localhost:5000/resultados/18/Hogar           # un registro
curl -X POST   http://localhost:5000/resultados -H 'Content-Type: application/json' \
     -d '{"hora":3,"categoria":"Prueba","total_ingresos":100.5,"num_ventas":3}'
curl -X PUT    http://localhost:5000/resultados/3/Prueba -H 'Content-Type: application/json' \
     -d '{"total_ingresos":200,"num_ventas":5}'
curl -X DELETE http://localhost:5000/resultados/3/Prueba

# 9. Persistencia: los datos siguen tras bajar y subir
docker compose down
docker compose up -d
curl http://localhost:5000/resultados/18
```

> Si cambias `API_PORT` en `.env`, vuelve a ejecutar `docker compose up -d`.

## Resultado esperado

240 líneas (hora 0–23 × 10 categorías). Las primeras y últimas:

```
0    Abarrotes    169829844.38   20734
0    Bebidas      170386194.98   21115
0    Deportes     168341612.85   20749
0    Electronica  169172381.17   20829
...
23   Papeleria    169336822.62   20762
23   Ropa         170759677.40   20993
```

La suma de `num_ventas` de las 240 líneas debe ser **5,000,000**. (Validado de forma independiente con pandas.)

## Tiempos medidos (C2)

| Método | Tiempo real |
|---|---|
| Hadoop Streaming (standalone) | 12.181 s |
| Python secuencial | 4.607 s |

¿Coinciden los resultados? `diff` → **Sí**

**Explicación:** En este caso el script de Python fue más rápido que Hadoop (4.6 s contra 12.2 s,
más o menos 2.6 veces). Esto pasa porque Hadoop en modo standalone corre en una sola computadora,
así que no puede repartir el trabajo entre varias máquinas. Además,
antes de empezar a procesar tiene que hacer varias cosas: arrancar Java, preparar el trabajo,
abrir un proceso de Python para cada tarea, ordenar los resultados intermedios y guardarlos en
archivos. Todo eso toma tiempo. El archivo de 350 MB no es tan grande, y Python lo lee de corrido
en una sola pasada sin tanto trámite. Hadoop se vuelve mejor cuando los datos son gigantescos y no
caben en una sola computadora, o cuando hay muchas máquinas trabajando al mismo tiempo.

## Evidencias (carpeta `evidencias/`)

-`hadoop version`
-`ssh localhost` y `ssh hadoop@hadoop` desde `api` sin contraseña
-Salida del job (`part-00000`) y tiempos
-Respuesta de `GET /resultados` y `GET /resultados/<clave>`
-POST/PUT/DELETE funcionando
-`docker compose down` / `up` y datos persistentes

## Parte E – Teoría

**1. Explica la diferencia entre los modos standalone, pseudo-distribuido y totalmente distribuido de Hadoop. ¿En cuál de ellos se usa HDFS?.** *Standalone*: un solo proceso Java, sin demonios y usando el sistema de archivos local (sin HDFS); sirve para desarrollar y probar. *Pseudo-distribuido*: todos los demonios (NameNode, DataNode, ResourceManager…) corren en una misma máquina como procesos separados, simulando un clúster; requiere SSH sin contraseña. *Totalmente distribuido*: los demonios se reparten entre varios nodos reales. HDFS se usa en pseudo-distribuido y en totalmente distribuido (no en standalone).

**2. ¿Por qué el dataset se monta como volumen y no se copia dentro de la imagen con COPY?** (1) La imagen quedaría de ~350 MB más, lenta de construir, subir y descargar, y cada cambio de datos obligaría a reconstruirla. (2) Los datos no son parte del software: deben poder cambiarse sin reconstruir. (3) Datos y código tienen ciclos de vida distintos; con volumen en solo lectura (`:ro`) además se protege el dataset original. (4) Se evita publicar datos en capas de imagen o en el repositorio.

**3. ¿Qué ocurre con los datos de la base de datos al ejecutar docker compose down? ¿Y con docker compose down -v?** `down` elimina contenedores y redes, pero **conserva los volúmenes nombrados**, por lo que los datos de PostgreSQL siguen ahí al volver a hacer `up`. `down -v` también **borra los volúmenes**, y la base de datos se pierde (hay que recargar los resultados).

**4. ¿Por qué MapReduce no siempre es más rápido que un script secuencial con un archivo de 400 MB? ¿A partir de qué condiciones conviene?** Porque tiene sobrecosto fijo: arranque de JVM, planificación, shuffle/sort y escritura de intermedios; en un solo equipo con 400 MB un script secuencial lee el archivo una vez y termina antes. Conviene cuando el volumen supera la memoria/disco de una máquina (decenas de GB a TB), cuando hay un clúster que paralelice, o cuando el cómputo por registro es pesado y los datos ya están distribuidos (HDFS, localidad de datos).

**5. Diferencia entre CMD y ENTRYPOINT, y entre COPY y ADD.** `ENTRYPOINT` define el ejecutable fijo del contenedor; `CMD` da los argumentos/comando por defecto y se puede sobrescribir fácilmente con `docker run <img> otro-comando` (con `ENTRYPOINT`, `CMD` se pasa como argumentos). `COPY` solo copia archivos del contexto a la imagen; `ADD` hace lo mismo pero además descomprime tar locales y puede descargar URLs, por eso se recomienda `COPY` salvo que se necesiten esas funciones.