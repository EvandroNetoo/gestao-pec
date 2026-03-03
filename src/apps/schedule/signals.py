"""
Signals de sincronização automática de alocações.

• m2m_changed em Aluno.oficinas_fixas
    - Aluno adicionado a oficina  → alocado (Previsto) em eventos futuros desta oficina
    - Aluno removido de oficina   → alocações Previsto removidas de eventos futuros

• m2m_changed em Evento.oficinas
    - Oficina adicionada ao evento → alunos da oficina alocados (Previsto) no evento
    - Oficina removida do evento   → alocações Previsto dos alunos da oficina removidas
                                     (salvo se o aluno pertence a outra oficina do evento)

Ambos os signals são conectados em ScheduleConfig.ready() (apps.py).
"""


def _on_aluno_oficinas_changed(sender, instance, action, pk_set, **kwargs):
    """Disparado quando Aluno.oficinas_fixas ou Oficina.alunos muda."""
    if action not in ('post_add', 'post_remove') or not pk_set:
        return

    from django.utils import timezone

    from schedule.models import AlocacaoPresenca, Aluno, Evento, Oficina

    agora = timezone.now()

    # ── Forward: aluno.oficinas_fixas.add/remove(oficinas) ──────────
    if isinstance(instance, Aluno):
        aluno = instance
        oficinas = list(Oficina.objects.filter(pk__in=pk_set))
        eventos_futuros = list(
            Evento.objects.filter(
                oficinas__in=oficinas,
                data_hora_inicio__gt=agora,
                cancelado=False,
            ).distinct()
        )
        if not eventos_futuros:
            return

        if action == 'post_add':
            ja_alocados = set(
                AlocacaoPresenca.objects.filter(
                    evento__in=eventos_futuros, aluno=aluno
                ).values_list('evento_id', flat=True)
            )
            AlocacaoPresenca.objects.bulk_create(
                [
                    AlocacaoPresenca(
                        evento=ev,
                        aluno=aluno,
                        status=AlocacaoPresenca.Status.PREVISTO,
                    )
                    for ev in eventos_futuros
                    if ev.pk not in ja_alocados
                ],
                ignore_conflicts=True,
            )
        else:
            AlocacaoPresenca.objects.filter(
                evento__in=eventos_futuros,
                aluno=aluno,
                status=AlocacaoPresenca.Status.PREVISTO,
            ).delete()

    # ── Reverse: oficina.alunos.add/remove(alunos) ──────────────────
    else:
        oficina = instance
        alunos = list(Aluno.objects.filter(pk__in=pk_set))
        eventos_futuros = list(
            Evento.objects.filter(
                oficinas=oficina,
                data_hora_inicio__gt=agora,
                cancelado=False,
            )
        )
        if not eventos_futuros:
            return

        if action == 'post_add':
            ja_alocados_pairs = set(
                AlocacaoPresenca.objects.filter(
                    evento__in=eventos_futuros, aluno__in=alunos
                ).values_list('evento_id', 'aluno_id')
            )
            AlocacaoPresenca.objects.bulk_create(
                [
                    AlocacaoPresenca(
                        evento=ev,
                        aluno=al,
                        status=AlocacaoPresenca.Status.PREVISTO,
                    )
                    for ev in eventos_futuros
                    for al in alunos
                    if (ev.pk, al.pk) not in ja_alocados_pairs
                ],
                ignore_conflicts=True,
            )
        else:
            AlocacaoPresenca.objects.filter(
                evento__in=eventos_futuros,
                aluno__in=alunos,
                status=AlocacaoPresenca.Status.PREVISTO,
            ).delete()


def _on_evento_oficinas_changed(sender, instance, action, pk_set, **kwargs):
    """Disparado quando Evento.oficinas muda."""
    if action not in ('post_add', 'post_remove') or not pk_set:
        return

    from schedule.models import AlocacaoPresenca, Aluno, Evento, Oficina

    if not isinstance(instance, Evento):
        return  # lado reverso não é esperado neste projeto

    evento = instance
    oficinas_modificadas = list(Oficina.objects.filter(pk__in=pk_set))

    if action == 'post_add':
        ja_alocados = set(evento.alocacoes.values_list('aluno_id', flat=True))
        alunos = list(
            Aluno.objects
            .filter(oficinas_fixas__in=oficinas_modificadas)
            .exclude(pk__in=ja_alocados)
            .distinct()
        )
        AlocacaoPresenca.objects.bulk_create(
            [
                AlocacaoPresenca(
                    evento=evento,
                    aluno=al,
                    status=AlocacaoPresenca.Status.PREVISTO,
                )
                for al in alunos
            ],
            ignore_conflicts=True,
        )
    else:
        # Após post_remove, evento.oficinas já reflete o estado novo
        oficinas_restantes = list(evento.oficinas.all())
        alunos_a_remover = Aluno.objects.filter(
            oficinas_fixas__in=oficinas_modificadas
        ).distinct()
        if oficinas_restantes:
            alunos_a_remover = alunos_a_remover.exclude(
                oficinas_fixas__in=oficinas_restantes
            )
        AlocacaoPresenca.objects.filter(
            evento=evento,
            aluno__in=alunos_a_remover,
            status=AlocacaoPresenca.Status.PREVISTO,
        ).delete()
