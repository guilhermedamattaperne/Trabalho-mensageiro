import pika
import time

RABBITMQ_HOST = '192.168.1.124'
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'

try:
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    connection_params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials
    )

    conexao = pika.BlockingConnection(connection_params)
    canal = conexao.channel()

    print(f"[OK] Conectado ao RabbitMQ em {RABBITMQ_HOST}:{RABBITMQ_PORT}")

    canal.queue_declare(queue='pedidos', durable=True)

    pizzas = ['Calabresa', 'Margherita', 'Frango', '4 Queijos', 'Portuguesa']

    for i, pizza in enumerate(pizzas, start=1):
        mensagem = f'Pedido #{i}: Pizza {pizza}'

        canal.basic_publish(
            exchange='',
            routing_key='pedidos',
            body=mensagem,
            properties=pika.BasicProperties(delivery_mode=2)
        )

        print(f'[Atendente] Pedido enviado: {mensagem}')
        time.sleep(0.5)

    print('[Atendente] Todos os pedidos foram enviados!')
    conexao.close()

except pika.exceptions.AMQPConnectionError as e:
    print(f"[ERRO] Não foi possível conectar: {e}")

except Exception as e:
    print(f"[ERRO] Erro inesperado: {e}")