import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import io
import locale

# Configura separador decimal para vírgula
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except:
    locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")

st.title("Visualizador de Arquivos .Result")

uploaded_files = st.file_uploader("Carregue um ou mais arquivos .result", type=["result"], accept_multiple_files=True)

# Definição das subfaixas
subfaixas = {
    "Serviços de interesse coletivo": [
        (461, 468), (864, 894), (758, 803), (943.5, 960),
        (1427, 1517), (1805, 1880), (1890, 1910), (2110, 2170),
        (2300, 2390), (2570, 2620), (2620, 2690), (3300, 3700),
        (24250, 27500)
    ],
    "Drones": [
        (433, 435), (902, 928), (1166, 1186), (1217, 1237),
        (1565, 1585), (2400, 2483.5), (5150, 5850)
    ],
    "WiFi": [
        (902, 928), (2400, 2483.5), (5150, 5850), (5925, 7125)
    ]
}

if uploaded_files:
    for idx, uploaded_file in enumerate(uploaded_files):
        st.subheader(f"Arquivo: {uploaded_file.name}")

        # Lê o arquivo em UTF-16
        content = uploaded_file.read().decode("utf-16")

        # Pega apenas os dados após [TableValues]
        if "[TableValues]" in content:
            table_data = content.split("[TableValues]")[1].strip().splitlines()

            # Lê como DataFrame
            df = pd.DataFrame([line.split("\t") for line in table_data])

            # Usa cabeçalhos definidos anteriormente no arquivo
            headers = ["Frequency_MHz", "MaxPeak", "Average", "Height_cm", "Polarization", "Correction_dB", "Comment"]
            df.columns = headers

            # Converte colunas numéricas
            df = df.apply(pd.to_numeric, errors='ignore')

            # Unidades vindas do cabeçalho do arquivo (se existirem)
            unit_line = [line for line in content.splitlines() if line.startswith("Unit=")]
            y_units = ""
            if unit_line:
                parts = unit_line[0].split("\t")
                if len(parts) > 2:
                    y_units = parts[2]  # unidade da coluna MaxPeak/Average

            # Nome padrão do eixo Y dependendo da unidade
            default_ylabel = "Nível"
            if y_units.lower() == "dbm":
                default_ylabel = "Potência (dBm)"
            elif y_units.lower() in ["dbuv/m", "dbµv/m", "dbμv/m"]:
                default_ylabel = "Intensidade de campo a 3 m (dBµV/m)"

            # Opção de título do gráfico
            title = st.text_input(f"Título para o gráfico de {uploaded_file.name}", value=f"Gráfico - {uploaded_file.name}", key=f"title_{idx}")

            # Seleção de curvas múltiplas (agora ambas são padrão)
            options = st.multiselect(
                f"Selecione as curvas para {uploaded_file.name}",
                ["MaxPeak", "Average"],
                default=["MaxPeak", "Average"],
                key=f"curves_{idx}"
            )

            # Limites do eixo X + Atenuador + opções adicionais
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                x_min = st.number_input("Frequência mínima (MHz)", value=float(df["Frequency_MHz"].min()), key=f"xmin_{idx}")
            with col2:
                x_max = st.number_input("Frequência máxima (MHz)", value=float(df["Frequency_MHz"].max()), key=f"xmax_{idx}")
            with col3:
                attenuator_db = st.number_input("Atenuador (dB)", value=0.0, step=0.1, key=f"att_{idx}")
            with col4:
                x_log = st.checkbox("Eixo X logarítmico", value=False, key=f"xlog_{idx}")
            with col5:
                show_subfaixas = st.checkbox("Exibir subfaixas autorizadas", value=False, key=f"subfaixas_{idx}")

            # Marcadores definidos pelo usuário (campo + cor na mesma linha)
            st.markdown("### Marcadores de frequência")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            markers = []
            for m, col_m in enumerate([col_m1, col_m2, col_m3, col_m4]):
                with col_m:
                    c1, c2 = st.columns([3,1])
                    with c1:
                        freq = st.text_input(f"M{m+1} (MHz)", value="0", key=f"marker_freq_{idx}_{m}")
                    try:
                        freq_val = float(freq.replace(",", "."))
                    except:
                        freq_val = 0.0
                    with c2:
                        color = st.color_picker("", value=["#2ECC71", "#9B59B6", "#E74C3C", "#F1C40F"][m], key=f"marker_color_{idx}_{m}")
                        st.markdown("<style>div[data-baseweb='color-picker']{transform: scale(0.7);}</style>", unsafe_allow_html=True)
                    if freq_val > 0 and x_min <= freq_val <= x_max:
                        if "MaxPeak" in df.columns:
                            y_val = np.interp(freq_val, df["Frequency_MHz"], df["MaxPeak"] - attenuator_db)
                            markers.append((freq_val, y_val, color))

            # Proteção contra limites inválidos
            if x_log:
                if x_min <= 0:
                    x_min = max(df["Frequency_MHz"].min(), 1e-3)
                if x_max <= x_min:
                    x_max = df["Frequency_MHz"].max()
                ax_scale = "log"
            else:
                if x_max <= x_min:
                    x_max = df["Frequency_MHz"].max()
                ax_scale = "linear"

            # Definição de cores padrão para cada curva
            default_colors = {"MaxPeak": "#55B5F9", "Average": "#FF975B"}

            # Configuração de estilo da linha para cada curva (Cor, Espessura, Estilo na mesma linha)
            st.markdown("### Estilo das curvas")
            col_left, col_right = st.columns(2)
            style_config = {}
            for opt, col_sel in zip(["MaxPeak", "Average"], [col_left, col_right]):
                if opt in options:
                    with col_sel:
                        st.markdown(f"**{opt}**")
                        c1, c2, c3 = st.columns([1,1,1])
                        with c1:
                            color = st.color_picker(
                                f"Cor {opt}", 
                                value=default_colors.get(opt, "#1f77b4"), 
                                key=f"color_{opt}_{idx}"
                            )
                        with c2:
                            linewidth = st.slider(f"Espessura {opt}", 1, 5, 2, key=f"lw_{opt}_{idx}")
                        with c3:
                            linestyle = st.selectbox(
                                f"Estilo {opt}",
                                ["-", "--", "-.", ":"],
                                format_func=lambda x: {"-":"Contínua", "--":"Tracejada", "-.":"Traço-ponto", ":":"Pontilhada"}[x],
                                key=f"ls_{opt}_{idx}"
                            )
                        style_config[opt] = {"color": color, "linewidth": linewidth, "linestyle": linestyle}

            # Plot com Matplotlib
            fig, ax = plt.subplots(figsize=(8,4))
            for opt in options:
                ax.plot(
                    df["Frequency_MHz"],
                    df[opt] - attenuator_db,
                    label=opt,
                    color=style_config[opt]["color"],
                    linewidth=style_config[opt]["linewidth"],
                    linestyle=style_config[opt]["linestyle"]
                )

            # Adiciona marcadores
            for i, (mx, my, mcolor) in enumerate(markers):
                ax.plot(mx, my, "o", color=mcolor, label=f"{str(mx).replace('.', ',')} MHz, {str(round(my,1)).replace('.', ',')} {y_units}")

            # Adiciona subfaixas, se ativado (sem legenda)
            if show_subfaixas:
                colors = {"Serviços de interesse coletivo":"#FFCDD2", "Drones":"#C8E6C9", "WiFi":"#BBDEFB"}
                for categoria, faixas in subfaixas.items():
                    for (f_start, f_end) in faixas:
                        if f_end < x_min or f_start > x_max:
                            continue
                        ax.axvspan(f_start, f_end, color=colors[categoria], alpha=0.4)

            ax.set_xscale(ax_scale)
            # Configuração de eixos e ticks
            ax.set_xlabel("Frequência (MHz)")
            ax.set_ylabel(default_ylabel)
            ax.set_title(title)

            if x_log:
                ax.set_xscale("log")
                start_pow = int(np.floor(np.log10(x_min)))
                end_pow = int(np.ceil(np.log10(x_max)))
                major_ticks = []
                for p in range(start_pow, end_pow + 1):
                    decade = 10 ** p
                    for s in range(1, 10):
                        val = s * decade
                        if x_min <= val <= x_max:
                            major_ticks.append(val)
                major_ticks.extend([x_min, x_max])
                major_ticks = sorted(set(major_ticks))

                ax.xaxis.set_major_locator(ticker.FixedLocator(major_ticks))
                ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f"{int(round(x))}" if abs(x - round(x)) < 1e-6 else f"{x:g}".replace(".", ",")))

                ax.xaxis.set_minor_locator(ticker.LogLocator(base=10.0, subs=range(2, 10)))
                ax.xaxis.set_minor_formatter(ticker.NullFormatter())
                ax.set_xlim(x_min, x_max)
            else:
                ax.set_xlim(x_min, x_max)
                current_ticks = list(ax.get_xticks())
                if x_min not in current_ticks:
                    current_ticks.append(x_min)
                if x_max not in current_ticks:
                    current_ticks.append(x_max)
                ax.xaxis.set_major_locator(ticker.FixedLocator(sorted(set(current_ticks))))
                ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f"{int(round(x))}" if abs(x - round(x)) < 1e-6 else f"{x:g}".replace(".", ",")))

            ax.grid(True, which="both", linestyle="--", linewidth=0.5)
            ax.legend()

            st.pyplot(fig)

            # Download PNG
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            st.download_button(
                label="📥 Baixar gráfico PNG",
                data=buf.getvalue(),
                file_name=f"{uploaded_file.name}_plot.png",
                mime="image/png",
                key=f"download_{idx}"
            )

            # Download CSV contendo apenas Frequency_MHz, MaxPeak e Average
            csv_buf = io.StringIO()
            df_export = df[["Frequency_MHz", "MaxPeak", "Average"]]
            df_export.to_csv(csv_buf, index=False, sep=";", decimal=",")
            st.download_button(
                label="📥 Baixar dados CSV",
                data=csv_buf.getvalue(),
                file_name=f"{title}.csv",
                mime="text/csv",
                key=f"download_csv_{idx}"
            )

        else:
            st.error("Seção [TableValues] não encontrada no arquivo.")