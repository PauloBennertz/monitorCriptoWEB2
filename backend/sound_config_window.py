# sound_config_window.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttkb
import os
import json
from core_components import get_application_path

class SoundConfigWindow:
    def __init__(self, parent_window, app_instance):
        self.parent_window = parent_window
        self.app_instance = app_instance
        self.config = app_instance.config

        # Cria a janela
        self.window = ttkb.Toplevel(parent_window)
        self.window.title("Configuração de Sons")
        self.window.geometry("550x700") # Aumentado o tamanho padrão
        self.window.resizable(True, True) # Permitir redimensionamento

        # Centraliza a janela
        self._center_window()

        # Configura a janela
        self.window.transient(parent_window)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self._close_window)

        # Carrega configurações de som
        self.sound_config = self.config.get('sound_config', {})

        # Cria a interface
        self._create_ui()

    def _center_window(self):
        """Centraliza a janela na tela."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _create_ui(self):
        """Cria a interface da janela."""
        # Frame principal
        main_frame = ttkb.Frame(self.window, padding=15, relief="solid", borderwidth=1)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        title_label = ttkb.Label(main_frame, text="Configuração de Sons de Alerta",
                                font=("-weight bold", 16), bootstyle="primary")
        title_label.pack(pady=(0, 20))

        # Frame para scroll
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttkb.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttkb.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas = canvas
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        # Configurações de som
        self._create_sound_configs(scrollable_frame)

        # Botões
        self._create_buttons(main_frame)

    def _create_sound_configs(self, parent_frame):
        """Cria as configurações de som."""
        # Sons disponíveis
        sound_options = [
            ("Alerta Padrão", "default_alert", os.path.join("sons", "Alerta.mp3")),
            ("Sobrecompra", "overbought", os.path.join("sons", "sobrecomprado.wav")),
            ("Sobrecompra (Alternativo)", "overbought_alt", os.path.join("sons", "sobrecomprado2.wav")),
            ("Cruzamento de Alta", "golden_cross", os.path.join("sons", "cruzamentoAlta.wav")),
            ("Cruzamento de Baixa", "death_cross", os.path.join("sons", "cruzamentoBaixa.wav")),
            ("Preço Acima", "price_above", os.path.join("sons", "precoAcima.wav")),
            ("Preço Abaixo", "price_below", os.path.join("sons", "precoAbaixo.wav")),
            ("Volume Alto", "high_volume", os.path.join("sons", "volumeAlto.wav")),
            ("Múltiplos Alertas", "multiple_alerts", os.path.join("sons", "multiplos_alertas.wav")),
            ("Alerta Crítico", "critical_alert", os.path.join("sons", "alertaCritico.wav"))
        ]

        # Título da seção
        section_label = ttkb.Label(parent_frame, text="Configurar Sons por Tipo de Alerta",
                                  font=("-weight bold", 12), bootstyle="info")
        section_label.pack(pady=(0, 15))

        # Variáveis para armazenar os caminhos
        self.sound_vars = {}

        for i, (name, key, default_path) in enumerate(sound_options):
            # Frame para cada configuração
            config_frame = ttkb.Frame(parent_frame, padding="5")
            config_frame.pack(fill=tk.X, pady=2)

            # Label do nome
            name_label = ttkb.Label(config_frame, text=f"{name}:",
                                   font=("-weight bold", 10), width=20)
            name_label.pack(side="left")

            # Entry para o caminho
            path_var = tk.StringVar(value=self.sound_config.get(key, default_path))
            self.sound_vars[key] = path_var

            path_entry = ttkb.Entry(config_frame, textvariable=path_var, width=30)
            path_entry.pack(side="left", padx=(5, 5))

            # Botão para selecionar arquivo
            browse_button = ttkb.Button(config_frame, text="Procurar",
                                       command=lambda k=key, v=path_var: self._browse_sound_file(k, v),
                                       bootstyle="outline-secondary")
            browse_button.pack(side="left", padx=(0, 5))

            # Botão para testar som
            test_button = ttkb.Button(config_frame, text="Testar",
                                     command=lambda v=path_var: self._test_sound(v.get()),
                                     bootstyle="outline-success")
            test_button.pack(side="left")

        # Seção de informações
        info_frame = ttkb.Frame(parent_frame, padding="10")
        info_frame.pack(fill=tk.X, pady=(20, 0))

        info_label = ttkb.Label(info_frame,
                               text="💡 Dica: Use arquivos .wav ou .mp3. O som 'Múltiplos Alertas' será usado quando vários alertas aparecerem simultaneamente.",
                               wraplength=450, justify=tk.LEFT, bootstyle="secondary")
        info_label.pack()

    def _on_mousewheel(self, event):
        """Permite a rolagem da lista com o scroll do mouse."""
        if event.num == 5 or event.delta == -120:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            self.canvas.yview_scroll(-1, "units")

    def _browse_sound_file(self, key, path_var):
        """Abre diálogo para selecionar arquivo de som."""
        file_path = filedialog.askopenfilename(
            title=f"Selecionar arquivo de som para {key}",
            filetypes=[("Arquivos de som", "*.wav *.mp3"), ("Todos os arquivos", "*.*")]
        )

        if file_path:
            # Converte para caminho relativo se possível
            app_path = get_application_path()
            if file_path.startswith(app_path):
                file_path = os.path.relpath(file_path, app_path)

            path_var.set(file_path)

    def _test_sound(self, sound_path):
        """Testa o som selecionado."""
        if not sound_path:
            messagebox.showwarning("Aviso", "Nenhum arquivo de som selecionado.")
            return

        try:
            from notification_service import play_alert_sound
            play_alert_sound(sound_path)
            messagebox.showinfo("Teste", "Som reproduzido com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao reproduzir som: {e}")

    def _create_buttons(self, parent_frame):
        """Cria os botões da janela."""
        button_frame = ttkb.Frame(parent_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        # Botão Salvar
        save_button = ttkb.Button(button_frame, text="Salvar",
                                 command=self._save_config,
                                 bootstyle="success")
        save_button.pack(side="right", padx=(5, 0))

        # Botão Cancelar
        cancel_button = ttkb.Button(button_frame, text="Cancelar",
                                   command=self._close_window,
                                   bootstyle="danger")
        cancel_button.pack(side="right")

        # Botão Restaurar Padrões
        reset_button = ttkb.Button(button_frame, text="Restaurar Padrões",
                                  command=self._reset_defaults,
                                  bootstyle="warning")
        reset_button.pack(side="left")

    def _save_config(self):
        """Salva as configurações de som."""
        try:
            # Coleta todas as configurações
            new_sound_config = {}
            for key, var in self.sound_vars.items():
                new_sound_config[key] = var.get()

            # Atualiza a configuração
            self.config['sound_config'] = new_sound_config

            # Salva no arquivo
            self.app_instance.save_config()

            messagebox.showinfo("Sucesso", "Configurações de som salvas com sucesso!")
            self._close_window()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar configurações: {e}")

    def _reset_defaults(self):
        """Restaura as configurações padrão."""
        if messagebox.askyesno("Confirmar", "Deseja restaurar as configurações padrão?"):
            # Restaura valores padrão
            defaults = {
                "default_alert": os.path.join("sons", "Alerta.mp3"),
                "overbought": os.path.join("sons", "sobrecomprado.wav"),
                "overbought_alt": os.path.join("sons", "sobrecomprado2.wav"),
                "golden_cross": os.path.join("sons", "cruzamentoAlta.wav"),
                "death_cross": os.path.join("sons", "cruzamentoBaixa.wav"),
                "price_above": os.path.join("sons", "precoAcima.wav"),
                "price_below": os.path.join("sons", "precoAbaixo.wav"),
                "high_volume": os.path.join("sons", "volumeAlto.wav"),
                "multiple_alerts": os.path.join("sons", "multiplos_alertas.wav"),
                "critical_alert": os.path.join("sons", "alertaCritico.wav")
            }

            for key, default_value in defaults.items():
                if key in self.sound_vars:
                    self.sound_vars[key].set(default_value)

    def _close_window(self):
        """Fecha a janela."""
        self.window.destroy()