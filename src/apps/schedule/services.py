from django.db import transaction

from schedule.models import (
    AlocacaoPresenca,
    Aluno,
    Evento,
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
