from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum


class Semestre(models.Model):
    nome = models.CharField('Nome', max_length=10, unique=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Semestre'
        verbose_name_plural = 'Semestres'
        ordering = ['-nome']

    def __str__(self):
        return self.nome


class Turma(models.Model):
    nome = models.CharField('Nome', max_length=150)
    semestre = models.ForeignKey(
        Semestre,
        on_delete=models.PROTECT,
        related_name='turmas',
        verbose_name='Semestre',
    )

    class Meta:
        verbose_name = 'Turma'
        verbose_name_plural = 'Turmas'
        ordering = ['-semestre__nome', 'nome']

    def __str__(self):
        return f'{self.nome} — {self.semestre}'


class Oficina(models.Model):
    nome = models.CharField('Nome', max_length=150)
    local_padrao = models.CharField('Local padrão', max_length=200)

    class Meta:
        verbose_name = 'Oficina'
        verbose_name_plural = 'Oficinas'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Aluno(models.Model):
    nome = models.CharField('Nome', max_length=200)
    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        related_name='alunos',
        verbose_name='Turma',
    )
    oficinas_fixas = models.ManyToManyField(
        Oficina,
        blank=True,
        related_name='alunos',
        verbose_name='Oficinas fixas',
    )

    class Meta:
        verbose_name = 'Aluno'
        verbose_name_plural = 'Alunos'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def total_presencas(self) -> int:
        total = (
            self.alocacoes.filter(
                status=AlocacaoPresenca.Status.PRESENTE,
                evento__cancelado=False,
            )
            .aggregate(total=Sum('evento__peso_presenca'))
            .get('total')
        )
        return total or 0


class Evento(models.Model):
    class Tipo(models.TextChoices):
        PERIODICO = 'Periódico', 'Periódico'
        ESPORADICO = 'Esporádico', 'Esporádico'

    titulo = models.CharField('Título', max_length=200)
    oficinas = models.ManyToManyField(
        Oficina,
        blank=True,
        related_name='eventos',
        verbose_name='Oficinas',
    )
    tipo = models.CharField(
        'Tipo',
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.PERIODICO,
    )
    data_hora_inicio = models.DateTimeField('Início')
    data_hora_fim = models.DateTimeField('Fim')
    local = models.CharField(
        'Local', max_length=200, blank=True, null=True
    )
    peso_presenca = models.IntegerField('Peso da presença', default=1)
    cancelado = models.BooleanField('Cancelado', default=False)

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['data_hora_inicio']

    def __str__(self):
        return self.titulo

    def get_local_definitivo(self) -> str:
        if self.local:
            return self.local
        primeira_oficina = self.oficinas.first()
        if primeira_oficina:
            return primeira_oficina.local_padrao
        return '—'


class AlocacaoPresenca(models.Model):
    class Status(models.TextChoices):
        PREVISTO = 'Previsto', 'Previsto'
        PRESENTE = 'Presente', 'Presente'
        AUSENTE = 'Ausente', 'Ausente'
        DISPENSADO = 'Dispensado', 'Dispensado'

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name='alocacoes',
        verbose_name='Evento',
    )
    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE,
        related_name='alocacoes',
        verbose_name='Aluno',
    )
    status = models.CharField(
        'Status',
        max_length=20,
        choices=Status.choices,
        default=Status.PREVISTO,
    )

    class Meta:
        verbose_name = 'Alocação / Presença'
        verbose_name_plural = 'Alocações / Presenças'
        unique_together = ['evento', 'aluno']

    def __str__(self):
        return f'{self.aluno} — {self.evento} ({self.status})'

    def clean(self):
        super().clean()
        if self.status not in (self.Status.PREVISTO, self.Status.PRESENTE):
            return

        conflitos = AlocacaoPresenca.objects.filter(
            aluno=self.aluno,
            status__in=[self.Status.PREVISTO, self.Status.PRESENTE],
        ).filter(
            Q(
                evento__data_hora_inicio__lt=self.evento.data_hora_fim,
                evento__data_hora_fim__gt=self.evento.data_hora_inicio,
            )
        )

        if self.pk:
            conflitos = conflitos.exclude(pk=self.pk)

        if conflitos.exists():
            eventos_conflito = ', '.join(
                str(a.evento) for a in conflitos[:3]
            )
            raise ValidationError(
                f'Conflito de horário: o aluno já está alocado em: '
                f'{eventos_conflito}.'
            )

    def save(self, *args, **kwargs):
        skip_validation = kwargs.pop('skip_validation', False)
        if not skip_validation:
            self.full_clean()
        super().save(*args, **kwargs)
