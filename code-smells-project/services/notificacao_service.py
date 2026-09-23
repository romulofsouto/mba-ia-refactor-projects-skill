import logging

from models.pedido import STATUS_APROVADO, STATUS_CANCELADO

logger = logging.getLogger(__name__)


def notificar_pedido_criado(pedido_id, usuario_id):
    # Integrações reais (e-mail, SMS, push) ainda não existem; apenas registra o evento.
    logger.info("Notificação: pedido %s criado para usuario %s (email/sms/push)", pedido_id, usuario_id)


def notificar_mudanca_status(pedido_id, status):
    if status == STATUS_APROVADO:
        logger.info("Notificação: pedido %s aprovado, preparar envio", pedido_id)
    elif status == STATUS_CANCELADO:
        logger.info("Notificação: pedido %s cancelado, devolver estoque", pedido_id)
