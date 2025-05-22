import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import uuid

st.set_page_config(page_title="Dashboard Universal", layout="wide")
st.title("Bienvenidos a Dashboard Universal")

# 🔗 Conexión a base de datos SQLite
conn = sqlite3.connect("datos.db", check_same_thread=False)
cursor = conn.cursor()

# 📄 Detectar separador
def detectar_separador(archivo):
    texto = archivo.read().decode("utf-8", errors="ignore")
    archivo.seek(0)
    if texto.count(';') > texto.count(','):
        return ';'
    elif texto.count('\t') > texto.count(','):
        return '\t'
    return ','

# 🔄 Crear tabla con nombre basado en archivo
def crear_tabla_y_guardar(df, file_name):
    # Limpiar y normalizar nombre del archivo para usar como tabla
    base_name = file_name.replace(".csv", "").replace(" ", "_").replace("-", "_")
    table_name = base_name + "_" + str(uuid.uuid4().hex[:6])

    df.columns = [col.replace(" ", "_") for col in df.columns]  # Normalizar columnas

    columnas_sql = []
    for col in df.columns:
        tipo = "TEXT"
        if pd.api.types.is_integer_dtype(df[col]):
            tipo = "INTEGER"
        elif pd.api.types.is_float_dtype(df[col]):
            tipo = "REAL"
        columnas_sql.append(f'"{col}" {tipo}')

    sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columnas_sql)});'
    cursor.execute(sql)

    placeholders = ', '.join(['?'] * len(df.columns))
    insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders});'
    cursor.executemany(insert_sql, df.values.tolist())
    conn.commit()

    return table_name

# 📤 SUBIR ARCHIVO
uploaded_file = st.file_uploader("📂 Sube un archivo CSV", type=["csv"])

if uploaded_file:
    file_name = uploaded_file.name
    sep = detectar_separador(uploaded_file)
    df = pd.read_csv(uploaded_file, sep=sep, on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)

    table_name = crear_tabla_y_guardar(df, file_name)
    st.success(f"✅ Datos guardados en la tabla: `{table_name}`")

# 📚 VER TABLAS GUARDADAS
st.subheader("📊 Tablas guardadas en la base de datos")

tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
table_names = [t[0] for t in tables]

selected_table = st.selectbox("Selecciona una tabla para visualizar", table_names)

if selected_table:
    df_db = pd.read_sql_query(f'SELECT * FROM "{selected_table}"', conn)
    st.dataframe(df_db)

    num_rows = st.slider("🔢 Cantidad de filas a analizar", 1, len(df_db), min(100, len(df_db)))
    df_subset = df_db.head(num_rows)

    numeric_cols = df_db.select_dtypes(include='number').columns.tolist()
    all_cols = df_db.columns.tolist()

    st.subheader("🎨 Gráfico interactivo")
    col1, col2 = st.columns(2)

    with col1:
        x_axis = st.selectbox("Eje X", options=all_cols)

    with col2:
        y_axis = st.selectbox("Eje Y (opcional)", options=["(ninguna)"] + numeric_cols)

    chart_type = st.selectbox("Tipo de gráfico", ["Barras", "Dispersión", "Histograma", "Pastel", "Boxplot"])

    fig = None

    if chart_type == "Barras":
        if y_axis != "(ninguna)":
            fig = px.bar(df_subset, x=x_axis, y=y_axis)
        else:
            count_data = df_subset[x_axis].value_counts().reset_index()
            count_data.columns = [x_axis, 'count']
            fig = px.bar(count_data, x=x_axis, y='count')

    elif chart_type == "Dispersión" and y_axis != "(ninguna)":
        fig = px.scatter(df_subset, x=x_axis, y=y_axis)

    elif chart_type == "Histograma":
        fig = px.histogram(df_subset, x=x_axis)

    elif chart_type == "Pastel":
        pie_data = df_subset[x_axis].value_counts().reset_index()
        pie_data.columns = [x_axis, 'count']
        fig = px.pie(pie_data, names=x_axis, values='count')

    elif chart_type == "Boxplot" and y_axis != "(ninguna)":
        fig = px.box(df_subset, x=x_axis, y=y_axis)

    if fig is not None:
        fig.update_layout(autosize=True)
        st.plotly_chart(fig, use_container_width=True, key=f"plot_{selected_table}_{chart_type}")
    else:
        st.warning("⚠️ Este gráfico necesita una columna numérica para el eje Y.")
