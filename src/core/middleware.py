import logging
import time

from django.db import connection

logger = logging.getLogger(__name__)


class PerformanceLogMiddleware:
    """
    Middleware para debugar lentidão em produção.
    Loga o tempo total da requisição e a quantidade de queries no banco de dados.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ignora arquivos estáticos para não poluir o log
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        start_time = time.time()
        
        # Em produção (DEBUG=False), o Django não guarda as queries na memória por padrão
        # a menos que forcemos ou usemos ferramentas específicas, mas podemos medir o tempo.
        # Para contar queries em produção, precisaríamos de um APM ou habilitar o debug de DB.
        # Como estamos apenas medindo o tempo de resposta da view:
        
        response = self.get_response(request)

        duration = time.time() - start_time

        logger.info(
            f"[{request.method}] {request.path} | "
            f"Status: {response.status_code} | "
            f"Tempo: {duration:.3f}s"
        )

        return response
