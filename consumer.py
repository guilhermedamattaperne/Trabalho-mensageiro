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
    canal.basic_qos(prefetch_count=1)

    def processar_pedido(ch, method, properties, body):
        pedido = body.decode()
        print(f'[Cozinheiro] Recebeu: {pedido}')
        time.sleep(2)
        print(f'[Cozinheiro] Pronto! {pedido} entregue!')
        ch.basic_ack(delivery_tag=method.delivery_tag)

    canal.basic_consume(queue='pedidos', on_message_callback=processar_pedido)

    print('[Cozinheiro] Cozinha aberta! Aguardando pedidos... (CTRL+C para parar)')
    canal.start_consuming()

except pika.exceptions.AMQPConnectionError as e:
    print(f"[ERRO] Não foi possível conectar: {e}")

except KeyboardInterrupt:
    print('\n[Cozinheiro] Cozinha fechada!')
    conexao.close()

except Exception as e:
    print(f"[ERRO] Erro inesperado: {e}")