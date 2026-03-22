import tkinter as tk
from tkinter import ttk, scrolledtext
import pika
import threading
import time
import random
from datetime import datetime

# ─── CONFIGURAÇÕES ───────────────────────────────────────────
RABBITMQ_HOST = '192.168.1.124'
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'
QUEUE_NAME = 'pedidos'

PIZZAS = ['Calabresa', 'Margherita', 'Frango', '4 Queijos',
          'Portuguesa', 'Pepperoni', 'Atum', 'Napolitana']

# ─── CORES ───────────────────────────────────────────────────
COR_BG        = '#1e1e2e'
COR_PAINEL    = '#2a2a3e'
COR_BORDA     = '#3d3d5c'
COR_ROXO      = '#7c6af7'
COR_ROXO2     = '#5a4fcf'
COR_VERDE     = '#4caf88'
COR_VERDE2    = '#2e7d5e'
COR_LARANJA   = '#f0a500'
COR_VERMELHO  = '#e05555'
COR_TEXTO     = '#e0e0f0'
COR_MUTED     = '#8888aa'
COR_AMARELO   = '#f5c842'

class PizzariaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pizzaria RabbitMQ — Sistema de Pedidos")
        self.root.configure(bg=COR_BG)
        self.root.geometry("980x680")
        self.root.resizable(False, False)

        # Estado
        self.cozinheiros_ativos = False
        self.pedidos_enviados = 0
        self.pedidos_entregues = 0
        self.fila_items = []
        self.threads_consumers = []
        self.parar_consumers = threading.Event()
        self.contador_pedido = 0
        self.lock = threading.Lock()

        self._build_ui()
        self.log("Sistema iniciado! Configure e comece a usar.", "info")

    # ─── BUILD UI ────────────────────────────────────────────
    def _build_ui(self):
        # Título
        titulo = tk.Frame(self.root, bg=COR_BG)
        titulo.pack(fill='x', padx=16, pady=(14, 4))
        tk.Label(titulo, text="Pizzaria RabbitMQ", font=("Segoe UI", 18, "bold"),
                 bg=COR_BG, fg=COR_ROXO).pack(side='left')
        tk.Label(titulo, text="Sistema de Mensageria — Sistemas Distribuídos",
                 font=("Segoe UI", 10), bg=COR_BG, fg=COR_MUTED).pack(side='left', padx=12, pady=4)

        # Linha separadora
        tk.Frame(self.root, bg=COR_BORDA, height=1).pack(fill='x', padx=16, pady=2)

        # Contadores
        self._build_contadores()

        # Corpo principal
        corpo = tk.Frame(self.root, bg=COR_BG)
        corpo.pack(fill='both', expand=True, padx=16, pady=6)

        # Coluna esquerda — controles + fila
        esq = tk.Frame(corpo, bg=COR_BG)
        esq.pack(side='left', fill='both', expand=True)
        self._build_controles(esq)
        self._build_fila(esq)

        # Coluna direita — cozinheiros + log
        dir_ = tk.Frame(corpo, bg=COR_BG)
        dir_.pack(side='right', fill='both', expand=True, padx=(10, 0))
        self._build_cozinheiros(dir_)
        self._build_log(dir_)

    def _build_contadores(self):
        frame = tk.Frame(self.root, bg=COR_BG)
        frame.pack(fill='x', padx=16, pady=6)

        cards = [
            ("Enviados",   lambda: self.pedidos_enviados,   COR_ROXO,    'enviados'),
            ("Na fila",    lambda: len(self.fila_items),    COR_LARANJA, 'fila_count'),
            ("Entregues",  lambda: self.pedidos_entregues,  COR_VERDE,   'entregues'),
        ]

        self.stat_labels = {}
        for titulo, _, cor, key in cards:
            card = tk.Frame(frame, bg=COR_PAINEL, bd=0, highlightthickness=1,
                            highlightbackground=COR_BORDA)
            card.pack(side='left', expand=True, fill='both', padx=6, pady=2, ipady=8)
            tk.Label(card, text=titulo, font=("Segoe UI", 9),
                     bg=COR_PAINEL, fg=COR_MUTED).pack()
            lbl = tk.Label(card, text="0", font=("Segoe UI", 26, "bold"),
                           bg=COR_PAINEL, fg=cor)
            lbl.pack()
            self.stat_labels[key] = lbl

    def _build_controles(self, pai):
        frame = tk.LabelFrame(pai, text=" Controles ", font=("Segoe UI", 9, "bold"),
                              bg=COR_PAINEL, fg=COR_MUTED, bd=1,
                              highlightbackground=COR_BORDA, labelanchor='nw')
        frame.pack(fill='x', pady=(0, 8), ipady=8, ipadx=8)

        # Botão enviar 1 pedido
        tk.Button(frame, text="Enviar 1 pedido",
                  font=("Segoe UI", 10, "bold"), bg=COR_ROXO, fg='white',
                  activebackground=COR_ROXO2, relief='flat', cursor='hand2',
                  padx=14, pady=7,
                  command=lambda: self._enviar_pedidos(1)).pack(side='left', padx=6, pady=4)

        # Botão enviar 5 pedidos
        tk.Button(frame, text="Enviar 5 pedidos",
                  font=("Segoe UI", 10), bg=COR_PAINEL, fg=COR_ROXO,
                  activebackground=COR_BORDA, relief='flat', cursor='hand2',
                  padx=14, pady=7, highlightthickness=1, highlightbackground=COR_ROXO,
                  command=lambda: self._enviar_pedidos(5)).pack(side='left', padx=6, pady=4)

        # Botão enviar 10 pedidos
        tk.Button(frame, text="Acumular fila (10)",
                  font=("Segoe UI", 10), bg=COR_PAINEL, fg=COR_LARANJA,
                  activebackground=COR_BORDA, relief='flat', cursor='hand2',
                  padx=14, pady=7, highlightthickness=1, highlightbackground=COR_LARANJA,
                  command=lambda: self._enviar_pedidos(10)).pack(side='left', padx=6, pady=4)

        # Botão cozinha
        self.btn_cozinha = tk.Button(frame, text="Ligar Cozinha",
                  font=("Segoe UI", 10, "bold"), bg=COR_VERDE, fg='white',
                  activebackground=COR_VERDE2, relief='flat', cursor='hand2',
                  padx=14, pady=7,
                  command=self._toggle_cozinha)
        self.btn_cozinha.pack(side='left', padx=6, pady=4)

        # Botão limpar log
        tk.Button(frame, text="Limpar log",
                  font=("Segoe UI", 9), bg=COR_PAINEL, fg=COR_MUTED,
                  activebackground=COR_BORDA, relief='flat', cursor='hand2',
                  padx=10, pady=7,
                  command=self._limpar_log).pack(side='right', padx=6, pady=4)

    def _build_fila(self, pai):
        frame = tk.LabelFrame(pai, text=" Fila de pedidos (Queue: 'pedidos') ",
                              font=("Segoe UI", 9, "bold"),
                              bg=COR_PAINEL, fg=COR_MUTED, bd=1,
                              highlightbackground=COR_BORDA, labelanchor='nw')
        frame.pack(fill='both', expand=True, pady=(0, 4), ipady=4, ipadx=4)

        self.fila_frame = tk.Frame(frame, bg=COR_PAINEL)
        self.fila_frame.pack(fill='both', expand=True, padx=4, pady=4)

        self.fila_vazia_label = tk.Label(self.fila_frame, text="Fila vazia — envie um pedido!",
                                          font=("Segoe UI", 9, "italic"),
                                          bg=COR_PAINEL, fg=COR_MUTED)
        self.fila_vazia_label.pack(pady=20)

    def _build_cozinheiros(self, pai):
        frame = tk.LabelFrame(pai, text=" Cozinheiros (Consumers) ",
                              font=("Segoe UI", 9, "bold"),
                              bg=COR_PAINEL, fg=COR_MUTED, bd=1,
                              highlightbackground=COR_BORDA, labelanchor='nw')
        frame.pack(fill='x', pady=(0, 8), ipady=6, ipadx=6)

        self.chef_frames = []
        self.chef_labels = []
        self.chef_status = []
        self.chef_bars = []

        for i in range(3):
            row = tk.Frame(frame, bg=COR_PAINEL)
            row.pack(fill='x', padx=8, pady=3)

            # Indicador
            dot = tk.Label(row, text="●", font=("Segoe UI", 12),
                           bg=COR_PAINEL, fg=COR_BORDA)
            dot.pack(side='left', padx=(0, 8))

            info = tk.Frame(row, bg=COR_PAINEL)
            info.pack(side='left', fill='x', expand=True)

            nome = tk.Label(info, text=f"Cozinheiro {i+1}",
                            font=("Segoe UI", 10, "bold"),
                            bg=COR_PAINEL, fg=COR_MUTED)
            nome.pack(anchor='w')

            status = tk.Label(info, text="Desligado",
                              font=("Segoe UI", 9),
                              bg=COR_PAINEL, fg=COR_BORDA)
            status.pack(anchor='w')

            self.chef_frames.append(dot)
            self.chef_labels.append(nome)
            self.chef_status.append(status)

    def _build_log(self, pai):
        frame = tk.LabelFrame(pai, text=" Log de eventos ",
                              font=("Segoe UI", 9, "bold"),
                              bg=COR_PAINEL, fg=COR_MUTED, bd=1,
                              highlightbackground=COR_BORDA, labelanchor='nw')
        frame.pack(fill='both', expand=True, ipady=4, ipadx=4)

        self.log_box = scrolledtext.ScrolledText(
            frame, font=("Consolas", 9), bg='#12121f', fg=COR_TEXTO,
            insertbackground=COR_TEXTO, relief='flat', bd=0,
            state='disabled', wrap='word'
        )
        self.log_box.pack(fill='both', expand=True, padx=4, pady=4)

        self.log_box.tag_config('info',    foreground='#8888cc')
        self.log_box.tag_config('producer', foreground=COR_ROXO)
        self.log_box.tag_config('consumer', foreground=COR_VERDE)
        self.log_box.tag_config('erro',    foreground=COR_VERMELHO)
        self.log_box.tag_config('sistema', foreground=COR_LARANJA)

    # ─── LÓGICA ──────────────────────────────────────────────
    def _conectar(self):
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        params = pika.ConnectionParameters(
            host=RABBITMQ_HOST, port=RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        conn = pika.BlockingConnection(params)
        ch = conn.channel()
        ch.queue_declare(queue=QUEUE_NAME, durable=True)
        return conn, ch

    def _enviar_pedidos(self, quantidade):
        def enviar():
            try:
                conn, ch = self._conectar()
                for _ in range(quantidade):
                    with self.lock:
                        self.contador_pedido += 1
                        num = self.contador_pedido
                    pizza = random.choice(PIZZAS)
                    msg = f"Pedido #{num}: Pizza {pizza}"
                    ch.basic_publish(
                        exchange='',
                        routing_key=QUEUE_NAME,
                        body=msg,
                        properties=pika.BasicProperties(delivery_mode=2)
                    )
                    self.pedidos_enviados += 1
                    self.root.after(0, lambda m=msg: self._add_fila(m))
                    self.root.after(0, self._atualizar_stats)
                    self.log(f"Atendente enviou: {msg}", "producer")
                    time.sleep(0.3)
                conn.close()
            except Exception as e:
                self.log(f"Erro ao enviar: {e}", "erro")

        threading.Thread(target=enviar, daemon=True).start()

    def _toggle_cozinha(self):
        if not self.cozinheiros_ativos:
            self._ligar_cozinha()
        else:
            self._desligar_cozinha()

    def _ligar_cozinha(self):
        self.cozinheiros_ativos = True
        self.parar_consumers.clear()
        self.btn_cozinha.config(text="Desligar Cozinha", bg=COR_VERMELHO,
                                activebackground='#aa3333')
        self.log("Cozinha aberta! 3 cozinheiros prontos.", "sistema")

        for i in range(3):
            self.chef_frames[i].config(fg=COR_AMARELO)
            self.chef_labels[i].config(fg=COR_TEXTO)
            self.chef_status[i].config(text="Aguardando pedido...", fg=COR_VERDE)
            t = threading.Thread(target=self._consumer_worker, args=(i,), daemon=True)
            t.start()
            self.threads_consumers.append(t)

    def _desligar_cozinha(self):
        self.cozinheiros_ativos = False
        self.parar_consumers.set()
        self.threads_consumers.clear()
        self.btn_cozinha.config(text="Ligar Cozinha", bg=COR_VERDE,
                                activebackground=COR_VERDE2)
        self.log("Cozinha fechada!", "sistema")

        for i in range(3):
            self.chef_frames[i].config(fg=COR_BORDA)
            self.chef_labels[i].config(fg=COR_MUTED)
            self.chef_status[i].config(text="Desligado", fg=COR_BORDA)

    def _consumer_worker(self, id_chef):
        try:
            conn, ch = self._conectar()
            ch.basic_qos(prefetch_count=1)

            def callback(ch2, method, properties, body):
                if self.parar_consumers.is_set():
                    ch2.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    return

                pedido = body.decode()
                self.root.after(0, lambda: self._chef_ocupado(id_chef, pedido))
                self.root.after(0, lambda m=pedido: self._rem_fila(m))
                self.log(f"Cozinheiro {id_chef+1} recebeu: {pedido}", "consumer")

                time.sleep(2)

                self.pedidos_entregues += 1
                self.root.after(0, lambda: self._chef_livre(id_chef))
                self.root.after(0, self._atualizar_stats)
                self.log(f"Cozinheiro {id_chef+1} entregou: {pedido} ✓ ACK", "consumer")
                ch2.basic_ack(delivery_tag=method.delivery_tag)

            ch.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

            while not self.parar_consumers.is_set():
                conn.process_data_events(time_limit=1)

            conn.close()
        except Exception as e:
            if self.cozinheiros_ativos:
                self.log(f"Cozinheiro {id_chef+1} erro: {e}", "erro")

    # ─── UI HELPERS ──────────────────────────────────────────
    def _add_fila(self, msg):
        self.fila_items.append(msg)
        self._render_fila()

    def _rem_fila(self, msg):
        if msg in self.fila_items:
            self.fila_items.remove(msg)
        self._render_fila()

    def _render_fila(self):
        for w in self.fila_frame.winfo_children():
            w.destroy()

        if not self.fila_items:
            tk.Label(self.fila_frame, text="Fila vazia — envie um pedido!",
                     font=("Segoe UI", 9, "italic"),
                     bg=COR_PAINEL, fg=COR_MUTED).pack(pady=20)
            return

        for item in self.fila_items:
            pill = tk.Frame(self.fila_frame, bg='#3a2f6e', bd=0,
                            highlightthickness=1, highlightbackground=COR_ROXO)
            pill.pack(fill='x', padx=4, pady=2)
            tk.Label(pill, text=item, font=("Segoe UI", 9),
                     bg='#3a2f6e', fg=COR_TEXTO, anchor='w',
                     padx=8, pady=4).pack(fill='x')

        self._atualizar_stats()

    def _chef_ocupado(self, i, pedido):
        pizza = pedido.split(": ")[-1] if ": " in pedido else pedido
        self.chef_frames[i].config(fg=COR_ROXO)
        self.chef_status[i].config(text=f"Fazendo: {pizza}...", fg=COR_ROXO)

    def _chef_livre(self, i):
        if self.cozinheiros_ativos:
            self.chef_frames[i].config(fg=COR_VERDE)
            self.chef_status[i].config(text="Aguardando pedido...", fg=COR_VERDE)

    def _atualizar_stats(self):
        self.stat_labels['enviados'].config(text=str(self.pedidos_enviados))
        self.stat_labels['fila_count'].config(text=str(len(self.fila_items)))
        self.stat_labels['entregues'].config(text=str(self.pedidos_entregues))

    def log(self, msg, tipo="info"):
        hora = datetime.now().strftime("%H:%M:%S")
        texto = f"[{hora}] {msg}\n"
        self.log_box.config(state='normal')
        self.log_box.insert('end', texto, tipo)
        self.log_box.see('end')
        self.log_box.config(state='disabled')

    def _limpar_log(self):
        self.log_box.config(state='normal')
        self.log_box.delete('1.0', 'end')
        self.log_box.config(state='disabled')

# ─── MAIN ────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = PizzariaApp(root)
    root.mainloop()
