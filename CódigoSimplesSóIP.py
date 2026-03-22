import pika
import time

# Conecta ao RabbitMQ em outra máquina
# Substitua '192.168.1.100' pelo IP da máquina que tem o RabbitMQ
conexao = pika.BlockingConnection(
    pika.ConnectionParameters('Colocar ip aqui')  # Exemplo 192.168.1.100
)
canal = conexao.channel()

# Restante do código igual...
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