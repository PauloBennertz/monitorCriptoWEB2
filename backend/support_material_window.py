# support_material_window.py
import tkinter as tk
import ttkbootstrap as ttkb
from tkinter import scrolledtext

class SupportMaterialWindow(ttkb.Toplevel):
    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.title("Material de Apoio (Filosofia)")
        self.geometry("700x500")
        self.transient(self.master)
        self.grab_set()

        self.setup_ui()
        self.parent_app.center_toplevel_on_main(self)

    def setup_ui(self):
        main_frame = ttkb.Frame(self, padding=15)
        main_frame.pack(expand=True, fill='both')

        text_content = """
        Material de Apoio: Filosofia por Trás do Monitoramento de Cripto

        Este monitor foi criado com base em algumas filosofias de investimento e trading:

        ----------------------------------------------------------------------
        1. Análise Técnica para Identificação de Tendências e Pontos de Entrada/Saída
        ----------------------------------------------------------------------

        Acreditamos que, embora o mercado de cripto seja volátil, padrões históricos de preço e volume tendem a se repetir, impulsionados pela psicologia humana. Os indicadores técnicos (RSI, Bollinger, MACD, MMEs) não são bolas de cristal, mas ferramentas para:

        -   **Identificar o momentum:** Onde o mercado está indo e com que força.
        -   **Reconhecer condições extremas:** Sobrecompra/Sobrevenda que podem preceder reversões.
        -   **Detectar cruzamentos importantes:** Sinais de mudança na tendência de curto e longo prazo.
        -   **Gerenciar o risco:** Definir níveis de entrada e saída com base em dados, não emoção.

        ----------------------------------------------------------------------
        2. Fluxo de Capital e Volume como Antecipadores de Preço
        ----------------------------------------------------------------------

        Uma grande movimentação de volume, especialmente em relação à capitalização de mercado de uma moeda, pode indicar um interesse institucional ou de grandes baleias que ainda não se refletiu totalmente no preço percentual.

        -   **Fuga de Capital:** Grandes volumes de venda em meio a uma queda de preço (mesmo que pequena) podem sugerir que grandes players estão saindo, indicando uma potencial queda mais acentuada no futuro próximo.
        -   **Entrada de Capital:** Grandes volumes de compra em meio a uma alta de preço (mesmo que pequena) podem sinalizar que grandes players estão acumulando, indicando um potencial aumento mais forte no futuro.

        Este é um dos dados mais valiosos para investidores que buscam se posicionar antes que a maioria do mercado reaja.

        ----------------------------------------------------------------------
        3. Automação para Reduzir o Viés Emocional
        ----------------------------------------------------------------------

        No trading, a emoção é o maior inimigo. O monitoramento automatizado permite:

        -   **Objetividade:** Alertas baseados em critérios pré-definidos, sem a interferência do medo ou ganância.
        -   **Eficiência:** Monitorar múltiplas moedas 24/7 sem a necessidade de olhar gráficos constantemente.
        -   **Disciplina:** Seguir seu plano de trade quando os gatilhos são acionados.

        ----------------------------------------------------------------------
        4. O Contexto Macro e Fundamentalista Importa
        ----------------------------------------------------------------------

        Embora esta ferramenta seja focada em dados técnicos e de fluxo de capital, é crucial combiná-la com:

        -   **Notícias macroeconômicas:** Inflação, taxas de juros, regulamentações.
        -   **Notícias específicas da moeda:** Desenvolvimento de projetos, parcerias, hacks, etc.
        -   **Sentimento geral do mercado:** Medo ou euforia.

        Use este monitor como uma parte da sua estratégia, não como a estratégia completa.

        """

        text_widget = scrolledtext.ScrolledText(main_frame, wrap='word', font=("Segoe UI", 10),
                                               bg="#2a2a2a", fg="white", insertbackground="white",
                                               state='disabled', relief='flat', padx=10, pady=10)
        text_widget.pack(expand=True, fill='both')

        text_widget.config(state='normal')
        text_widget.insert(tk.END, text_content)
        text_widget.config(state='disabled')