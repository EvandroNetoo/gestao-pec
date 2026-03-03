from django.apps import AppConfig


class ScheduleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schedule'

    def ready(self):
        from django.db.models.signals import m2m_changed

        from schedule.models import Aluno, Evento
        from schedule.signals import (
            _on_aluno_oficinas_changed,
            _on_evento_oficinas_changed,
        )

        m2m_changed.connect(
            _on_aluno_oficinas_changed,
            sender=Aluno.oficinas_fixas.through,
        )
        m2m_changed.connect(
            _on_evento_oficinas_changed,
            sender=Evento.oficinas.through,
        )
