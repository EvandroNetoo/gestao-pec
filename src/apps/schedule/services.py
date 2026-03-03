from django.db import transaction
from django.utils import timezone

from schedule.models import (
    AlocacaoPresenca,
    Aluno,
    Evento,
    Oficina,
    Semestre,
    Turma,
)


@transaction.atomic
def realocar_aluno(
    aluno: Aluno,
    evento_original: Evento,
    evento_novo: Evento,
) -> AlocacaoPresenca:
    """Dispensa o aluno do evento original e aloca no evento novo."""
    AlocacaoPresenca.objects.filter(
        aluno=aluno, evento=evento_original
    ).update(status=AlocacaoPresenca.Status.DISPENSADO)

    nova_alocacao = AlocacaoPresenca(
        aluno=aluno,
        evento=evento_novo,
        status=AlocacaoPresenca.Status.PREVISTO,
    )
    nova_alocacao.save(skip_validation=True)
    return nova_alocacao


@transaction.atomic
def copiar_turma(turma_origem: Turma, semestre_destino: Semestre) -> Turma:
    """Duplica a turma e todos os seus alunos para outro semestre."""
    alunos_originais = list(
        turma_origem.alunos.prefetch_related('oficinas_fixas')
    )

    nova_turma = Turma.objects.create(
        nome=turma_origem.nome,
        semestre=semestre_destino,
    )

    for aluno_original in alunos_originais:
        oficinas = list(aluno_original.oficinas_fixas.all())
        novo_aluno = Aluno.objects.create(
            nome=aluno_original.nome,
            turma=nova_turma,
        )
        if oficinas:
            novo_aluno.oficinas_fixas.set(oficinas)

    return nova_turma


@transaction.atomic
def alocar_alunos_de_oficinas(evento: Evento, oficinas) -> int:
    """Cria AlocacaoPresenca (Previsto) para todos os alunos das oficinas dadas.

    Ignora alunos já alocados ao evento.
    Retorna o número de novas alocações criadas.
    """
    aluno_ids_ja_alocados = set(
        evento.alocacoes.values_list('aluno_id', flat=True)
    )
    alunos = (
        Aluno.objects
        .filter(oficinas_fixas__in=oficinas)
        .exclude(pk__in=aluno_ids_ja_alocados)
        .distinct()
    )
    novas = [
        AlocacaoPresenca(
            evento=evento,
            aluno=aluno,
            status=AlocacaoPresenca.Status.PREVISTO,
        )
        for aluno in alunos
    ]
    AlocacaoPresenca.objects.bulk_create(novas, ignore_conflicts=True)
    return len(novas)


@transaction.atomic
def sincronizar_alunos_oficina(
    oficina: Oficina,
    alunos_adicionados,
    alunos_removidos,
) -> tuple[int, int]:
    """Sincroniza alocações em eventos FUTUROS desta oficina.

    - Alunos adicionados à oficina → alocados (Previsto) nos eventos futuros.
    - Alunos removidos da oficina → alocações Previsto removidas nos eventos
      futuros (não toca em Presente / Ausente / Dispensado).

    Retorna (qtd_adicionados, qtd_removidos).
    """
    agora = timezone.now()
    eventos_futuros = list(
        Evento.objects.filter(
            oficinas=oficina,
            data_hora_inicio__gt=agora,
            cancelado=False,
        )
    )

    adicionados_total = 0
    removidos_total = 0

    alunos_add_ids = [a.pk for a in alunos_adicionados]
    alunos_rem_ids = [a.pk for a in alunos_removidos]

    for evento in eventos_futuros:
        # Adicionar novos alunos
        if alunos_add_ids:
            ja_alocados = set(
                evento.alocacoes.filter(
                    aluno_id__in=alunos_add_ids
                ).values_list('aluno_id', flat=True)
            )
            novas = [
                AlocacaoPresenca(
                    evento=evento,
                    aluno_id=aluno_id,
                    status=AlocacaoPresenca.Status.PREVISTO,
                )
                for aluno_id in alunos_add_ids
                if aluno_id not in ja_alocados
            ]
            AlocacaoPresenca.objects.bulk_create(novas, ignore_conflicts=True)
            adicionados_total += len(novas)

        # Remover alunos que saíram (apenas status Previsto)
        if alunos_rem_ids:
            deleted_count, _ = AlocacaoPresenca.objects.filter(
                evento=evento,
                aluno_id__in=alunos_rem_ids,
                status=AlocacaoPresenca.Status.PREVISTO,
            ).delete()
            removidos_total += deleted_count

    return adicionados_total, removidos_total


@transaction.atomic
def sincronizar_alunos_evento(
    evento: Evento,
    oficinas_adicionadas,
    oficinas_removidas,
) -> tuple[int, int]:
    """Sincroniza alocações de um evento quando suas oficinas mudam.

    - Oficinas adicionadas → aloca alunos dessas oficinas no evento.
    - Oficinas removidas → remove alocações Previsto de alunos que NÃO
      pertencem a nenhuma das oficinas restantes do evento.

    Retorna (qtd_adicionados, qtd_removidos).
    """
    adicionados = 0
    removidos = 0

    # Alocar alunos de oficinas recém-adicionadas
    if oficinas_adicionadas:
        adicionados = alocar_alunos_de_oficinas(
            evento, list(oficinas_adicionadas)
        )

    # Remover alocações de alunos de oficinas removidas que não pertencem mais
    # a nenhuma oficina restante do evento
    if oficinas_removidas:
        oficinas_restantes = list(evento.oficinas.all())
        alunos_removidos_qs = Aluno.objects.filter(
            oficinas_fixas__in=list(oficinas_removidas)
        ).distinct()
        if oficinas_restantes:
            # Mantém quem ainda pertence a alguma oficina restante do evento
            alunos_removidos_qs = alunos_removidos_qs.exclude(
                oficinas_fixas__in=oficinas_restantes
            )
        deleted_count, _ = AlocacaoPresenca.objects.filter(
            evento=evento,
            aluno__in=alunos_removidos_qs,
            status=AlocacaoPresenca.Status.PREVISTO,
        ).delete()
        removidos += deleted_count

    return adicionados, removidos
