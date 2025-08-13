# -*- coding: utf-8 -*-
import sys
import subprocess

# ===============================
# 1. INSTALACIÓN DE LIBRERÍAS SOLO EN COLAB
# ===============================
if 'google.colab' in sys.modules:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "streamlit", "pandas", "sqlite3-to-sqlalchemy", "-q"
    ])

import sqlite3
import pandas as pd
import streamlit as st

# ===============================
# 2. CREAR BASE DE DATOS EN MEMORIA
# ===============================
conn = sqlite3.connect("torneos.db")
cursor = conn.cursor()

# ===============================
# 3. CREAR TABLAS (si no existen)
# ===============================
cursor.executescript("""
CREATE TABLE IF NOT EXISTS jugadores (
    id_jugador INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL,
    categoria TEXT NOT NULL,
    fecha_nacimiento TEXT,
    club TEXT,
    email TEXT,
    telefono TEXT
);

CREATE TABLE IF NOT EXISTS torneos (
    id_torneo INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_torneo TEXT NOT NULL,
    categoria TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    ubicacion TEXT
);

CREATE TABLE IF NOT EXISTS partidos (
    id_partido INTEGER PRIMARY KEY AUTOINCREMENT,
    id_torneo INTEGER NOT NULL,
    id_jugador1 INTEGER NOT NULL,
    id_jugador2 INTEGER NOT NULL,
    ganador INTEGER NOT NULL,
    fecha_partido TEXT NOT NULL,
    ronda TEXT,
    FOREIGN KEY (id_torneo) REFERENCES torneos(id_torneo),
    FOREIGN KEY (id_jugador1) REFERENCES jugadores(id_jugador),
    FOREIGN KEY (id_jugador2) REFERENCES jugadores(id_jugador),
    FOREIGN KEY (ganador) REFERENCES jugadores(id_jugador)
);
""")

# ===============================
# 4. INSERTAR DATOS SI NO EXISTEN
# ===============================
cursor.execute("SELECT COUNT(*) FROM jugadores")
if cursor.fetchone()[0] == 0:
    jugadores = [
        ("Juan Pérez", "A", "1990-04-15", "Club Centro", "juanperez@mail.com", "1122334455"),
        ("Carlos López", "A", "1988-10-02", "Club Norte", "carloslopez@mail.com", "1144556677"),
        ("Pedro Gómez", "B", "1995-06-21", "Club Sur", "pedrogomez@mail.com", "1133221100"),
        ("Luis Fernández", "A", "1992-09-11", "Club Centro", "luisfernandez@mail.com", "1177889900"),
    ]
    cursor.executemany("""
    INSERT INTO jugadores (nombre_completo, categoria, fecha_nacimiento, club, email, telefono)
    VALUES (?, ?, ?, ?, ?, ?)
    """, jugadores)

cursor.execute("SELECT COUNT(*) FROM torneos")
if cursor.fetchone()[0] == 0:
    torneos = [
        ("Abierto-Feb-2025", "A", "2025-02-10", "2025-02-15", "Buenos Aires"),
        ("Masters-Mar-2025", "B", "2025-03-05", "2025-03-10", "Rosario"),
    ]
    cursor.executemany("""
    INSERT INTO torneos (nombre_torneo, categoria, fecha_inicio, fecha_fin, ubicacion)
    VALUES (?, ?, ?, ?, ?)
    """, torneos)

cursor.execute("SELECT COUNT(*) FROM partidos")
if cursor.fetchone()[0] == 0:
    partidos = [
        (1, 1, 2, 1, "2025-02-10", "Cuartos"),
        (1, 1, 4, 4, "2025-02-12", "Semifinal"),
        (1, 4, 1, 1, "2025-02-15", "Final"),
        (2, 3, 1, 3, "2025-03-05", "Cuartos"),
        (2, 3, 2, 3, "2025-03-07", "Semifinal"),
        (2, 3, 4, 4, "2025-03-10", "Final"),
    ]
    cursor.executemany("""
    INSERT INTO partidos (id_torneo, id_jugador1, id_jugador2, ganador, fecha_partido, ronda)
    VALUES (?, ?, ?, ?, ?, ?)
    """, partidos)

conn.commit()

# ===============================
# 5. GENERAR RANKING EN TIEMPO REAL
# ===============================
query = """
SELECT j.id_jugador, j.nombre_completo, j.categoria,
       SUM(CASE WHEN p.ganador = j.id_jugador THEN 100 ELSE 0 END) +
       COUNT(*) * 10 +
       SUM(CASE WHEN p.ganador = j.id_jugador AND p.ronda = 'Final' THEN 200 ELSE 0 END) AS puntos,
       COUNT(DISTINCT p.id_torneo) AS torneos_jugados,
       SUM(CASE WHEN p.ganador = j.id_jugador AND p.ronda = 'Final' THEN 1 ELSE 0 END) AS torneos_ganados
FROM jugadores j
JOIN partidos p ON j.id_jugador IN (p.id_jugador1, p.id_jugador2)
GROUP BY j.id_jugador, j.nombre_completo, j.categoria
ORDER BY j.categoria, puntos DESC;
"""

df_ranking = pd.read_sql_query(query, conn)

# ===============================
# 6. MOSTRAR RESULTADOS EN STREAMLIT
# ===============================
st.title("🏆 Ranking de Torneos por Categoría")

for categoria in sorted(df_ranking['categoria'].unique()):
    st.subheader(f"Categoría {categoria}")
    df_categoria = df_ranking[df_ranking['categoria'] == categoria].copy()

    # Ordenar por puntos y agregar columna de posición
    df_categoria = df_categoria.sort_values(by="puntos", ascending=False).reset_index(drop=True)
    df_categoria.insert(0, "Posición", range(1, len(df_categoria) + 1))

    # Asegurar mínimo 5 jugadores (rellenar si faltan)
    while len(df_categoria) < 5:
        df_categoria.loc[len(df_categoria)] = [
            len(df_categoria) + 1,  # posición
            None,                   # id_jugador
            "Jugador Extra",        # nombre_completo
            categoria,              # categoria
            0,                      # puntos
            0,                      # torneos_jugados
            0                       # torneos_ganados
        ]

    st.dataframe(df_categoria)

conn.close()
