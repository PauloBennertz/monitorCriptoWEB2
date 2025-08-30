import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from monitoring_service import get_top_100_coins
import threading
import time

class DynamicViewWindow(ttkb.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Visão Dinâmica de Criptomoedas")
        self.geometry("1200x700")

        self.parent = parent
        self.running = True

        self.configure_styles()
        self.create_widgets()

        self.load_data()
        self.start_auto_refresh()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def configure_styles(self):
        style = ttkb.Style.get_instance()
        style.configure('Futuristic.Treeview', rowheight=30, font=("Segoe UI", 11))
        style.configure('Futuristic.Treeview.Heading', font=("Segoe UI", 12, "bold"))
        style.map('Futuristic.Treeview', background=[('selected', '#2a2a2a')])

    def create_widgets(self):
        main_frame = ttkb.Frame(self, padding=15)
        main_frame.pack(expand=True, fill=BOTH)

        header_frame = ttkb.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 15))

        header = ttkb.Label(header_frame, text="Top 100 Criptomoedas por Capitalização de Mercado", font=("Segoe UI", 16, "bold"), bootstyle="info")
        header.pack(side=LEFT)

        self.status_label = ttkb.Label(header_frame, text="", font=("Segoe UI", 10), bootstyle="secondary")
        self.status_label.pack(side=RIGHT, padx=10)

        self.tree = ttkb.Treeview(
            main_frame,
            columns=("rank", "coin", "price", "change_24h", "volume_24h", "market_cap"),
            show="headings",
            bootstyle="dark",
            style='Futuristic.Treeview'
        )

        self.tree.heading("rank", text="#")
        self.tree.heading("coin", text="Moeda")
        self.tree.heading("price", text="Preço")
        self.tree.heading("change_24h", text="Variação 24h")
        self.tree.heading("volume_24h", text="Volume 24h")
        self.tree.heading("market_cap", text="Capitalização de Mercado")

        self.tree.column("rank", width=50, anchor=CENTER)
        self.tree.column("coin", width=200, anchor=W)
        self.tree.column("price", width=150, anchor=E)
        self.tree.column("change_24h", width=150, anchor=E)
        self.tree.column("volume_24h", width=200, anchor=E)
        self.tree.column("market_cap", width=250, anchor=E)

        scrollbar = ttkb.Scrollbar(main_frame, orient=VERTICAL, command=self.tree.yview, bootstyle="round-dark")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=LEFT, expand=True, fill=BOTH)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.tree.tag_configure('positive', foreground='#4CAF50') # Verde
        self.tree.tag_configure('negative', foreground='#F44336') # Vermelho

    def load_data(self):
        self.after(0, self._update_status, "Atualizando...")
        data = get_top_100_coins()
        self.after(0, self._populate_tree, data)
        self.after(0, self._update_status, f"Atualizado em: {time.strftime('%H:%M:%S')}")

    def _populate_tree(self, data):
        # Preserva a seleção e a posição do scroll
        selected_item = self.tree.selection()
        scroll_pos = self.tree.yview()

        self.tree.delete(*self.tree.get_children())

        if not data:
            self.tree.insert("", END, values=("", "Não foi possível carregar os dados.", "", "", "", ""))
            return

        for i, coin in enumerate(data):
            rank = coin.get('market_cap_rank', 'N/A')
            name = f"{coin.get('name', 'N/A')} ({coin.get('symbol', 'N/A').upper()})"
            price = f"${coin.get('current_price', 0):,.4f}"
            change_24h = coin.get('price_change_percentage_24h', 0)
            change_24h_str = f"{change_24h:+.2f}%" if change_24h is not None else "N/A"
            volume_24h = f"${coin.get('total_volume', 0):,}"
            market_cap = f"${coin.get('market_cap', 0):,}"

            tag = ''
            if change_24h is not None:
                if change_24h > 0:
                    tag = 'positive'
                elif change_24h < 0:
                    tag = 'negative'

            values = (rank, name, price, change_24h_str, volume_24h, market_cap)
            self.tree.insert("", END, values=values, iid=i, tags=(tag,))

        # Restaura a seleção e a posição do scroll
        if selected_item:
            self.tree.selection_set(selected_item)
        self.tree.yview_moveto(scroll_pos[0])

    def _update_status(self, message):
        self.status_label.config(text=message)

    def start_auto_refresh(self):
        self.refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
        self.refresh_thread.start()

    def _auto_refresh_loop(self):
        while self.running:
            time.sleep(60)
            if self.running:
                self.load_data()

    def on_closing(self):
        self.running = False
        self.destroy()

if __name__ == '__main__':
    app = ttkb.Window(themename="darkly")
    dynamic_window = DynamicViewWindow(app)
    app.mainloop()
