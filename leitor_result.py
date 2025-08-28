import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from babel.numbers import format_decimal

# Função para formatar números com vírgula
def format_number(num):
    try:
        return format_decimal(num, locale='pt_BR')
    except:
        return str(num)

st.title("Visualizador de Arquivos .result")

uploaded_files = st.file_uploader("Carregar arquivos .result", type=["result"], accept_multiple_files=True)

for uploaded_file in uploaded_files:
    df = pd.read_csv(uploaded_file, sep='\t', comment='#')
    df.columns = [col.strip() for col in df.columns]

    # Conversão para MHz
    if "Frequency" in df.columns:
        df["Frequency_MHz"] = df["Frequency"] / 1e6
    else:
        continue

    st.subheader(f"Gráfico para {uploaded_file.name}")

    # Título do gráfico
    titulo = st.text_input(f"Título para {uploaded_file.name}", value=uploaded_file.name)

    # Limites do eixo X
    col1, col2, col3 = st.columns(3)
    with col1:
        x_min = st.number_input(f"Frequência mínima (MHz) - {uploaded_file.name}", value=float(df["Frequency_MHz"].min()), key=f"xmin_{uploaded_file.name}")
    with col2:
        x_max = st.number_input(f"Frequência máxima (MHz) - {uploaded_file.name}", value=float(df["Frequency_MHz"].max()), key=f"xmax_{uploaded_file.name}")
    with col3:
        atten = st.number_input(f"Atenuador (dB) - {uploaded_file.name}", value=0.0, key=f"atten_{uploaded_file.name}")

    # Seleção de curvas
    show_avg = st.checkbox(f"Exibir Average - {uploaded_file.name}", value=True, key=f"avg_{uploaded_file.name}")
    show_max = st.checkbox(f"Exibir MaxPeak - {uploaded_file.name}", value=True, key=f"max_{uploaded_file.name}")

    fig, ax = plt.subplots()

    if show_avg and "Average" in df.columns:
        ax.plot(df["Frequency_MHz"], df["Average"] - atten, label="Average")
    if show_max and "MaxPeak" in df.columns:
        ax.plot(df["Frequency_MHz"], df["MaxPeak"] - atten, label="MaxPeak")

    ax.set_xlim(x_min, x_max)

    # Definição da unidade no eixo Y
    unidade = ""
    if "dBm" in df.columns or "MaxPeak" in df.columns:
        unidade = "Potência (dBm)"
    elif "dBµV/m" in df.columns or "Average" in df.columns:
        unidade = "Intensidade de campo a 3m (dBµV/m)"
    else:
        unidade = "Valor"

    ax.set_xlabel("Frequência (MHz)")
    ax.set_ylabel(unidade)
    ax.legend()
    ax.grid(True, which="both", linestyle="--", linewidth=0.5)

    st.pyplot(fig)

    # Exportar CSV
    export_df = df[["Frequency_MHz", "MaxPeak", "Average"]].copy()
    csv = export_df.to_csv(index=False, sep="\t").encode("utf-8")
    st.download_button(
        label="Baixar CSV",
        data=csv,
        file_name=f"{titulo}.csv",
        mime="text/csv",
    )
