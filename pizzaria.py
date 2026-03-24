import tkinter as tk
from tkinter import ttk, scrolledtext
import pika
import threading
import time
import random
from datetime import datetime

# ---------------------------------------------------------------------------
# --- CONFIGURAÇÕES ---------------------------------------------------------
# ---------------------------------------------------------------------------
# ATENÇÃO: Altere para o IP do seu servidor RabbitMQ ou use 'localhost'
RABBITMQ_HOST = '192.168.101.14'
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'
QUEUE_NAME = 'pedidos'

PIZZAS = ['Calabresa', 'Margherita', 'Frango', '4 Queijos', 'Portuguesa', 'Pepperoni', 'Atum', 'Napolitana']

# ---------------------------------------------------------------------------
# --- CORES E ESTILOS (NEURODESIGN) -----------------------------------------
# ---------------------------------------------------------------------------
BG_DEEP      = '#0d0d1a'   # Fundo principal (profundo, foco)
BG_PANEL     = '#16162a'   # Painéis e cards (separação sutil)
BG_CARD      = '#1e1e35'   # Cards internos (destaque)
BG_ITEM      = '#1a1a30'   # Itens da fila (consistência)

# Bordas e separadores
BORDER_DIM   = '#2a2a4a'   # Borda sutil para não distrair

# Cores de ação — psicologia de cores
C_PURPLE     = '#7c6af7'   # Ação primária (confiança, tecnologia)
C_PURPLE_LT  = '#9d8fff'   # Roxo claro (hover)
C_PURPLE_DK  = '#5a4fcf'   # Roxo escuro (clique)

C_GREEN      = '#22c55e'   # Sucesso (entregue, ligado)
C_GREEN_LT   = '#4ade80'   # Verde claro (hover)
C_GREEN_DK   = '#16a34a'   # Verde escuro (clique)
C_GREEN_BG   = '#052e16'   # Fundo verde (badge)

C_ORANGE     = '#f59e0b'   # Atenção (fila, acumulando)
C_ORANGE_LT  = '#fbbf24'   # Laranja claro (hover)
C_ORANGE_DK  = '#d97706'   # Laranja escuro (clique)
C_ORANGE_BG  = '#2d1a00'   # Fundo laranja (badge)

C_RED        = '#ef4444'   # Erro / desligar
C_RED_LT     = '#f87171'   # Vermelho claro (hover)
C_RED_DK     = '#dc2626'   # Vermelho escuro (clique)
C_RED_BG     = '#2d0a0a'   # Fundo vermelho (badge)

C_YELLOW_LT  = '#fde047'   # Amarelo para status 'cozinhando'

# Texto
C_TEXT       = '#e2e2f0'   # Texto principal (legibilidade)
C_TEXT_DIM   = '#8888aa'   # Texto secundário (hierarquia)
C_WHITE      = '#ffffff'

# Cores do Log
LOG_PRODUCER = '#a78bfa'   # Roxo para produtor
LOG_CONSUMER = '#34d399'   # Verde para consumidor
LOG_ERROR    = '#f87171'   # Vermelho para erro
LOG_SYSTEM   = '#fbbf24'   # Laranja para sistema
LOG_TIME     = '#555577'   # Cinza para timestamp

# ÍCONES (emoji como reforço visual)
ICON_PIZZA   = '🍕'
ICON_SEND    = '📤'
ICON_QUEUE   = '📋'
ICON_CHEF    = '👨‍🍳'
ICON_CHECK   = '✅'
ICON_ERROR   = '❌'
ICON_SYSTEM  = '⚙️'
ICON_FIRE    = '🔥'
ICON_CLOCK   = '⏱'

# ---------------------------------------------------------------------------
# --- COMPONENTE: RoundedButton ---------------------------------------------
# ---------------------------------------------------------------------------
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None, bg=C_PURPLE, fg=C_WHITE, hover_bg=C_PURPLE_LT, active_bg=C_PURPLE_DK, font_size=10, font_weight='bold', width=160, height=38, radius=10, **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent.cget('bg'), highlightthickness=0, **kwargs)
        self._text = text
        self._command = command
        self._bg = bg
        self._fg = fg
        self._hover_bg = hover_bg
        self._active_bg = active_bg
        self._font = ("Helvetica", font_size, font_weight)
        self._radius = radius
        self._width = width
        self._height = height
        self._current = bg
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self, bg=None):
        self.delete("all")
        color = bg or self._current
        r, w, h = self._radius, self._width, self._height
        points = [r, 0, w - r, 0, w, 0, w, r, w, h - r, w, h, w - r, h, r, h, 0, h, 0, h - r, 0, r, 0, 0]
        self.create_polygon(points, smooth=True, fill=color)
        self.create_text(w // 2, h // 2, text=self._text, fill=self._fg, font=self._font, anchor='center')

    def _on_enter(self, _e=None): self._current = self._hover_bg; self._draw()
    def _on_leave(self, _e=None): self._current = self._bg; self._draw()
    def _on_press(self, _e=None): self._current = self._active_bg; self._draw()
    def _on_release(self, _e=None):
        self._current = self._hover_bg
        self._draw()
        if self._command: self._command()

    def config_text(self, text): self._text = text; self._draw()
    def config_colors(self, bg, hover, active): self._bg, self._hover_bg, self._active_bg, self._current = bg, hover, active, bg; self._draw()

# ---------------------------------------------------------------------------
# --- COMPONENTE: StatCard --------------------------------------------------
# ---------------------------------------------------------------------------
class StatCard(tk.Canvas):
    def __init__(self, parent, title, value_var, color, icon, width=200, height=100, radius=15, **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent.cget("bg"), highlightthickness=0, **kwargs)
        self._title, self._value_var, self._color, self._icon = title, value_var, color, icon
        self._width, self._height, self._radius = width, height, radius
        self.configure(bg=BG_DEEP)
        self._draw_card()
        self._value_var.trace_add("write", self._update_value)

    def _draw_card(self):
        self.delete("all")
        r, w, h = self._radius, self._width, self._height
        # Desenha o corpo arredondado do card
        points = [r, 0, w - r, 0, w, 0, w, r, w, h - r, w, h, w - r, h, r, h, 0, h, 0, h - r, 0, r, 0, 0]
        self.create_polygon(points, smooth=True, fill=BG_CARD, outline=BORDER_DIM)
        # Adiciona textos e ícone
        self.create_text(w // 2, 25, text=self._title, fill=C_TEXT_DIM, font=("Helvetica", 10, "bold"))
        self.create_text(w // 2 - 40, 65, text=self._icon, fill=self._color, font=("Helvetica", 22))
        self.value_text_id = self.create_text(w // 2 + 15, 65, text=self._value_var.get(), fill=self._color, font=("Helvetica", 28, "bold"))

    def _update_value(self, *args): self.itemconfig(self.value_text_id, text=self._value_var.get())

# ---------------------------------------------------------------------------
# --- APLICAÇÃO PRINCIPAL ---------------------------------------------------
# ---------------------------------------------------------------------------
class PizzariaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pizzaria RabbitMQ - Sistema de Pedidos Moderno")
        self.root.geometry("1100x750")
        self.root.configure(bg=BG_DEEP)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # --- Variáveis de Estado com Tkinter ---
        self.cozinheiros_ativos = False
        self.pedidos_enviados = tk.StringVar(value="0")
        self.pedidos_entregues = tk.StringVar(value="0")
        self.fila_count = tk.StringVar(value="0")
        self.rabbitmq_status = tk.StringVar(value="Verificando...")
        self.fila_items, self.threads_consumers = [], []
        self.parar_consumers = threading.Event()
        self.contador_pedido = 0
        self.lock = threading.Lock()

        self._build_ui()
        self.log(f"{ICON_SYSTEM} Sistema iniciado. Pressione 'Ligar Cozinha' para começar.", "system")
        self.root.after(500, self._verificar_rabbitmq_status)

    def _build_ui(self):
        # --- Header ---
        header = tk.Frame(self.root, bg=BG_DEEP)
        header.pack(pady=10, fill=tk.X, padx=20)
        title_frame = tk.Frame(header, bg=BG_DEEP)
        title_frame.pack(side=tk.LEFT)
        tk.Label(title_frame, text="Pizzaria RabbitMQ", font=("Helvetica", 22, "bold"), bg=BG_DEEP, fg=C_TEXT).pack(anchor="w")
        tk.Label(title_frame, text="Sistema de Mensageria — Sistemas Distribuídos", font=("Helvetica", 11), bg=BG_DEEP, fg=C_TEXT_DIM).pack(anchor="w")
        self.rabbitmq_status_label = tk.Label(header, textvariable=self.rabbitmq_status, font=("Helvetica", 10, "bold"), fg=C_WHITE, padx=10, pady=5)
        self.rabbitmq_status_label.pack(side=tk.RIGHT)
        self._atualizar_rabbitmq_status("Verificando...", C_ORANGE_BG, C_ORANGE_LT)

        # --- Painel de Stats ---
        stats_frame = tk.Frame(self.root, bg=BG_DEEP)
        stats_frame.pack(pady=10, fill=tk.X, padx=10)
        StatCard(stats_frame, "Pedidos Enviados", self.pedidos_enviados, C_PURPLE, ICON_SEND).pack(side=tk.LEFT, expand=True, padx=10)
        StatCard(stats_frame, "Pedidos na Fila", self.fila_count, C_ORANGE, ICON_QUEUE).pack(side=tk.LEFT, expand=True, padx=10)
        StatCard(stats_frame, "Pedidos Entregues", self.pedidos_entregues, C_GREEN, ICON_CHECK).pack(side=tk.LEFT, expand=True, padx=10)

        # --- Painel de Controle ---
        controls = tk.Frame(self.root, bg=BG_DEEP)
        controls.pack(pady=15)
        RoundedButton(controls, f"{ICON_SEND} Enviar 1 Pedido", lambda: self._enviar_pedidos(1), width=160).pack(side=tk.LEFT, padx=5)
        RoundedButton(controls, f"{ICON_SEND} Enviar 5 Pedidos", lambda: self._enviar_pedidos(5), width=160).pack(side=tk.LEFT, padx=5)
        self.btn_cozinha = RoundedButton(controls, f"{ICON_FIRE} Ligar Cozinha", self._toggle_cozinha, bg=C_GREEN, hover_bg=C_GREEN_LT, active_bg=C_GREEN_DK, width=160)
        self.btn_cozinha.pack(side=tk.LEFT, padx=5)

        # --- Área Principal (Fila e Logs) ---
        main_area = tk.Frame(self.root, bg=BG_DEEP)
        main_area.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)
        
        # --- Coluna da Esquerda (Fila e Cozinheiros) ---
        left_col = tk.Frame(main_area, bg=BG_DEEP)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        fila_container = tk.Frame(left_col, bg=BG_PANEL, highlightbackground=BORDER_DIM, highlightthickness=1)
        fila_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        tk.Label(fila_container, text=f"{ICON_QUEUE} Fila de Pedidos", font=("Helvetica", 13, "bold"), bg=BG_PANEL, fg=C_TEXT).pack(pady=10)
        self.fila_frame = tk.Frame(fila_container, bg=BG_PANEL)
        self.fila_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cozinheiros_container = tk.Frame(left_col, bg=BG_PANEL, height=150, highlightbackground=BORDER_DIM, highlightthickness=1)
        cozinheiros_container.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(cozinheiros_container, text=f"{ICON_CHEF} Cozinheiros", font=("Helvetica", 13, "bold"), bg=BG_PANEL, fg=C_TEXT).pack(pady=10)
        self.cozinheiros_labels = []
        for i in range(3):
            f = tk.Frame(cozinheiros_container, bg=BG_PANEL)
            f.pack(fill=tk.X, padx=15, pady=3)
            tk.Label(f, text=f"Cozinheiro {i+1}", font=("Helvetica", 11), bg=BG_PANEL, fg=C_TEXT).pack(side=tk.LEFT)
            lbl = tk.Label(f, text="Desligado", font=("Helvetica", 11, "italic"), bg=BG_PANEL, fg=C_RED)
            lbl.pack(side=tk.RIGHT)
            self.cozinheiros_labels.append(lbl)

        # --- Coluna da Direita (Logs) ---
        log_container = tk.Frame(main_area, bg=BG_PANEL, highlightbackground=BORDER_DIM, highlightthickness=1)
        log_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, ipadx=5)
        tk.Label(log_container, text=f"{ICON_SYSTEM} Log de Eventos", font=("Helvetica", 13, "bold"), bg=BG_PANEL, fg=C_TEXT).pack(pady=10)
        self.log_box = scrolledtext.ScrolledText(log_container, wrap=tk.WORD, bg=BG_ITEM, fg=C_TEXT, font=("Consolas", 10), state='disabled', relief=tk.FLAT, borderwidth=0, insertbackground=C_TEXT)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.log_box.tag_config('producer', foreground=LOG_PRODUCER)
        self.log_box.tag_config('consumer', foreground=LOG_CONSUMER)
        self.log_box.tag_config('erro', foreground=LOG_ERROR)
        self.log_box.tag_config('system', foreground=LOG_SYSTEM)
        self.log_box.tag_config('time', foreground=LOG_TIME)

    def _conectar(self):
        try:
            conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD), heartbeat=600, blocked_connection_timeout=300))
            ch = conn.channel()
            ch.queue_declare(queue=QUEUE_NAME, durable=True)
            self.root.after(0, self._atualizar_rabbitmq_status, "Conectado", C_GREEN_BG, C_GREEN_LT)
            return conn, ch
        except Exception as e:
            self.root.after(0, self._atualizar_rabbitmq_status, "Erro de Conexão", C_RED_BG, C_RED_LT)
            self.log(f"{ICON_ERROR} Falha ao conectar ao RabbitMQ: {e}", "erro")
            return None, None

    def _verificar_rabbitmq_status(self):
        threading.Thread(target=self._conectar_e_fechar, daemon=True).start()
        self.root.after(10000, self._verificar_rabbitmq_status) # Verifica a cada 10s

    def _conectar_e_fechar(self):
        conn, _ = self._conectar()
        if conn: conn.close()

    def _atualizar_rabbitmq_status(self, text, bg, fg):
        self.rabbitmq_status.set(text)
        self.rabbitmq_status_label.config(bg=bg, fg=fg)

    def _enviar_pedidos(self, quantidade):
        def enviar():
            conn, ch = self._conectar()
            if not (conn and ch): return
            try:
                for _ in range(quantidade):
                    with self.lock:
                        self.contador_pedido += 1
                        num = self.contador_pedido
                    pizza = random.choice(PIZZAS)
                    msg = f"Pedido #{num}: Pizza {pizza}"
                    ch.basic_publish(exchange='', routing_key=QUEUE_NAME, body=msg, properties=pika.BasicProperties(delivery_mode=2))
                    self.root.after(0, lambda m=msg: self._add_fila(m))
                    self.log(f"{ICON_SEND} Atendente enviou: {msg}", "producer")
                    time.sleep(0.1)
            except Exception as e:
                self.log(f"{ICON_ERROR} Erro ao enviar pedido: {e}", "erro")
            finally:
                if conn: conn.close()
        threading.Thread(target=enviar, daemon=True).start()

    def _toggle_cozinha(self):
        if not self.cozinheiros_ativos: self._ligar_cozinha()
        else: self._desligar_cozinha()

    def _ligar_cozinha(self):
        self.cozinheiros_ativos = True
        self.btn_cozinha.config_text(f"{ICON_FIRE} Desligar Cozinha")
        self.btn_cozinha.config_colors(C_RED, C_RED_LT, C_RED_DK)
        self.log(f"{ICON_FIRE} Cozinha aberta! Cozinheiros prontos.", "system")
        self.parar_consumers.clear()
        for i in range(3):
            t = threading.Thread(target=self._consumer_worker, args=(i,), daemon=True)
            self.threads_consumers.append(t)
            t.start()
            self.cozinheiros_labels[i].config(text="Livre", fg=C_GREEN)

    def _desligar_cozinha(self):
        self.cozinheiros_ativos = False
        self.btn_cozinha.config_text(f"{ICON_FIRE} Ligar Cozinha")
        self.btn_cozinha.config_colors(C_GREEN, C_GREEN_LT, C_GREEN_DK)
        self.log(f"{ICON_FIRE} Cozinha fechada!", "system")
        self.parar_consumers.set()
        for t in self.threads_consumers: t.join(timeout=1)
        self.threads_consumers = []
        for lbl in self.cozinheiros_labels: lbl.config(text="Desligado", fg=C_RED)

    def _consumer_worker(self, id_chef):
        conn, ch = self._conectar()
        if not (conn and ch): return
        def callback(ch, method, properties, body):
            pedido = body.decode()
            with self.lock:
                self.root.after(0, self._chef_ocupado, id_chef, pedido)
                self.root.after(0, self._rem_fila, pedido)
            self.log(f"{ICON_CHEF} Cozinheiro {id_chef+1} recebeu: {pedido}", "consumer")
            time.sleep(random.uniform(2, 5))
            with self.lock:
                self.root.after(0, self._chef_livre, id_chef)
                self.root.after(0, self.pedidos_entregues.set, str(int(self.pedidos_entregues.get()) + 1))
            self.log(f"{ICON_CHECK} Cozinheiro {id_chef+1} entregou: {pedido}", "consumer")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        ch.basic_qos(prefetch_count=1)
        ch.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
        try:
            while not self.parar_consumers.is_set(): conn.process_data_events(time_limit=1)
        except Exception as e:
            if self.cozinheiros_ativos: self.log(f"{ICON_ERROR} Cozinheiro {id_chef+1} perdeu conexão: {e}", "erro")
        finally:
            if conn.is_open: conn.close()

    def _add_fila(self, msg):
        self.fila_items.append(msg)
        self.pedidos_enviados.set(str(int(self.pedidos_enviados.get()) + 1))
        self._render_fila()

    def _rem_fila(self, msg):
        if msg in self.fila_items: self.fila_items.remove(msg)
        self._render_fila()

    def _render_fila(self):
        for widget in self.fila_frame.winfo_children(): widget.destroy()
        self.fila_count.set(str(len(self.fila_items)))
        if not self.fila_items:
            tk.Label(self.fila_frame, text="Fila vazia — envie um pedido!", font=("Helvetica", 11, "italic"), bg=BG_PANEL, fg=C_TEXT_DIM).pack(pady=10)
        else:
            for item in self.fila_items:
                tk.Label(self.fila_frame, text=f"{ICON_PIZZA} {item}", font=("Helvetica", 11), bg=BG_ITEM, fg=C_TEXT, padx=8, pady=4).pack(anchor="w", fill=tk.X, padx=5, pady=2)

    def _chef_ocupado(self, i, pedido): self.cozinheiros_labels[i].config(text=f"{ICON_CLOCK} Ocupado", fg=C_YELLOW_LT)
    def _chef_livre(self, i):
        if self.cozinheiros_ativos: self.cozinheiros_labels[i].config(text="Livre", fg=C_GREEN)

    def log(self, msg, tipo="system"):
        hora = datetime.now().strftime("[%H:%M:%S]")
        self.log_box.config(state='normal')
        self.log_box.insert('end', f"{hora} ", 'time')
        self.log_box.insert('end', f"{msg}\n", tipo)
        self.log_box.see('end')
        self.log_box.config(state='disabled')

    def _on_closing(self):
        if self.cozinheiros_ativos: self._desligar_cozinha()
        self.root.destroy()

# ---------------------------------------------------------------------------
# --- INICIALIZAÇÃO ---------------------------------------------------------
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = PizzariaApp(root)
    root.mainloop()