from django import forms
from django.forms import DateTimeInput

from schedule.models import (
    AlocacaoPresenca,
    Aluno,
    Evento,
    Oficina,
    Semestre,
    Turma,
)


# ── Semestre ───────────────────────────────────────────────────────
class SemestreForm(forms.ModelForm):
    class Meta:
        model = Semestre
        fields = ['nome', 'ativo']


# ── Turma ──────────────────────────────────────────────────────────
class TurmaForm(forms.ModelForm):
    class Meta:
        model = Turma
        fields = ['nome', 'semestre']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['semestre'].queryset = Semestre.objects.filter(ativo=True)


class CopiarTurmaForm(forms.Form):
    semestre_destino = forms.ModelChoiceField(
        queryset=Semestre.objects.filter(ativo=True),
        label='Semestre de destino',
    )


# ── Oficina ────────────────────────────────────────────────────────
class OficinaForm(forms.ModelForm):
    alunos = forms.ModelMultipleChoiceField(
        queryset=Aluno.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Alunos',
    )

    class Meta:
        model = Oficina
        fields = ['nome', 'local_padrao', 'semestre']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['semestre'].queryset = Semestre.objects.filter(ativo=True)
        self.fields['alunos'].queryset = (
            Aluno.objects
            .filter(turma__semestre__ativo=True)
            .select_related('turma')
            .order_by('turma__nome', 'nome')
        )
        self.fields['alunos'].label_from_instance = lambda aluno: f'{aluno.nome} ({aluno.turma.nome})'
        if self.instance.pk:
            self.fields['alunos'].initial = self.instance.alunos.values_list(
                'pk', flat=True
            )

    def save(self, commit=True):
        oficina = super().save(commit=commit)
        if commit:
            oficina.alunos.set(self.cleaned_data['alunos'])
        else:
            old_save_m2m = self.save_m2m

            def save_m2m():
                old_save_m2m()
                oficina.alunos.set(self.cleaned_data['alunos'])

            self.save_m2m = save_m2m
        return oficina


class OficinaBulkForm(forms.Form):
    """Adicionar várias oficinas de uma vez, uma por linha."""

    semestre = forms.ModelChoiceField(
        queryset=Semestre.objects.filter(ativo=True),
        label='Semestre',
    )
    oficinas = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'rows': 10,
                'placeholder': 'Uma oficina por linha, formato:\n'
                'Nome da Oficina | Local Padrão\n'
                'Ex:\nMúsica | Sala 101\nTeatro | Auditório\nDança | Sala 202',
            }
        ),
        label='Oficinas',
        help_text='Uma oficina por linha. Formato: nome | local padrão. '
        'Linhas em branco serão ignoradas.',
    )

    def clean_oficinas(self):
        raw = self.cleaned_data['oficinas']
        resultado = []
        for i, linha in enumerate(raw.splitlines(), 1):
            linha = linha.strip()
            if not linha:
                continue
            partes = linha.split('|')
            if len(partes) != 2:
                raise forms.ValidationError(
                    f'Linha {i}: formato inválido "{linha}". '
                    'Use: nome | local padrão'
                )
            nome = partes[0].strip()
            local = partes[1].strip()
            if not nome or not local:
                raise forms.ValidationError(
                    f'Linha {i}: nome e local padrão são obrigatórios.'
                )
            resultado.append({'nome': nome, 'local_padrao': local})
        if not resultado:
            raise forms.ValidationError('Informe ao menos uma oficina.')
        return resultado


# ── Aluno ──────────────────────────────────────────────────────────
class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = ['nome', 'turma', 'oficinas_fixas']
        widgets = {
            'oficinas_fixas': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['turma'].queryset = Turma.objects.filter(
            semestre__ativo=True
        ).select_related('semestre')
        self.fields['oficinas_fixas'].queryset = Oficina.objects.filter(
            semestre__ativo=True
        ).select_related('semestre')


class AlunoBulkForm(forms.Form):
    """Adicionar vários alunos de uma vez, um nome por linha."""

    turma = forms.ModelChoiceField(
        queryset=Turma.objects.filter(semestre__ativo=True).select_related(
            'semestre'
        ),
        label='Turma',
    )
    nomes = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'rows': 10,
                'placeholder': 'Digite um nome por linha\nEx:\nJoão Silva\nMaria Souza\nPedro Santos',
            }
        ),
        label='Nomes dos alunos',
        help_text='Um nome por linha. Linhas em branco serão ignoradas.',
    )

    def clean_nomes(self):
        raw = self.cleaned_data['nomes']
        nomes = [linha.strip() for linha in raw.splitlines() if linha.strip()]
        if not nomes:
            raise forms.ValidationError('Informe ao menos um nome.')
        return nomes


# ── Evento ─────────────────────────────────────────────────────────


class EventoCriarForm(forms.Form):
    """Formulário para criar evento(s), com suporte a recorrência."""

    PERIODO_CHOICES = [
        ('semanal', 'Semanal'),
        ('quinzenal', 'A cada 2 semanas'),
        ('personalizado', 'Personalizado'),
    ]

    titulo = forms.CharField(max_length=200, label='Título')
    tipo = forms.ChoiceField(
        choices=Evento.Tipo.choices,
        label='Tipo',
    )
    data = forms.DateField(
        label='Data inicial',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    hora_inicio = forms.TimeField(
        label='Hora de início',
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )
    hora_fim = forms.TimeField(
        label='Hora de fim',
        widget=forms.TimeInput(attrs={'type': 'time'}),
    )
    periodo = forms.ChoiceField(
        choices=PERIODO_CHOICES,
        label='Período de recorrência',
        required=False,
    )
    intervalo_dias = forms.IntegerField(
        label='Intervalo em dias',
        required=False,
        min_value=1,
    )
    data_fim_recorrencia = forms.DateField(
        label='Data final da recorrência',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    local = forms.CharField(
        max_length=200,
        required=False,
        label='Local',
    )
    peso_presenca = forms.IntegerField(
        initial=1,
        label='Peso da presença',
        min_value=1,
    )
    oficinas = forms.ModelMultipleChoiceField(
        queryset=Oficina.objects.filter(semestre__ativo=True).select_related('semestre'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Oficinas',
    )

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        hora_inicio = cleaned.get('hora_inicio')
        hora_fim = cleaned.get('hora_fim')

        if hora_inicio and hora_fim and hora_fim <= hora_inicio:
            raise forms.ValidationError(
                'A hora de fim deve ser posterior à hora de início.'
            )

        if tipo == Evento.Tipo.PERIODICO:
            periodo = cleaned.get('periodo')
            if not periodo:
                self.add_error(
                    'periodo', 'Selecione o período de recorrência.'
                )
            if periodo == 'personalizado' and not cleaned.get(
                'intervalo_dias'
            ):
                self.add_error(
                    'intervalo_dias', 'Informe o intervalo em dias.'
                )
            if not cleaned.get('data_fim_recorrencia'):
                self.add_error(
                    'data_fim_recorrencia',
                    'Informe a data final da recorrência.',
                )
            elif cleaned.get('data') and (
                cleaned['data_fim_recorrencia'] <= cleaned['data']
            ):
                self.add_error(
                    'data_fim_recorrencia',
                    'A data final deve ser posterior à data inicial.',
                )

        return cleaned


class EventoForm(forms.ModelForm):
    """Formulário para editar um evento existente."""

    class Meta:
        model = Evento
        fields = [
            'titulo',
            'tipo',
            'data_hora_inicio',
            'data_hora_fim',
            'local',
            'peso_presenca',
            'oficinas',
            'cancelado',
        ]
        widgets = {
            'data_hora_inicio': DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'data_hora_fim': DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'oficinas': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['oficinas'].queryset = Oficina.objects.filter(
            semestre__ativo=True
        ).select_related('semestre')
        self.fields['data_hora_inicio'].input_formats = [
            '%Y-%m-%dT%H:%M',
        ]
        self.fields['data_hora_fim'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('data_hora_inicio')
        fim = cleaned.get('data_hora_fim')
        if inicio and fim and fim <= inicio:
            raise forms.ValidationError(
                'A data/hora de fim deve ser posterior ao início.'
            )
        return cleaned


# ── Alocação / Presença ───────────────────────────────────────────
class AlocacaoPresencaForm(forms.ModelForm):
    class Meta:
        model = AlocacaoPresenca
        fields = ['aluno', 'status']


class AlocarAlunosForm(forms.Form):
    """Seleciona múltiplos alunos para alocar de uma vez."""

    alunos = forms.ModelMultipleChoiceField(
        queryset=Aluno.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label='Alunos',
    )

    def __init__(self, *args, evento: Evento, **kwargs):
        super().__init__(*args, **kwargs)
        ja_alocados = evento.alocacoes.values_list('aluno_id', flat=True)
        oficinas_evento = evento.oficinas.all()
        qs = Aluno.objects.filter(turma__semestre__ativo=True).exclude(
            pk__in=ja_alocados
        )
        if oficinas_evento.exists():
            qs = qs.filter(oficinas_fixas__in=oficinas_evento).distinct()
        self.fields['alunos'].queryset = qs


# ── Presença (público) ────────────────────────────────────────────
class PresencaForm(forms.Form):
    """Formulário dinâmico para registrar presenças de um evento."""

    def __init__(self, *args, evento: Evento, **kwargs):
        super().__init__(*args, **kwargs)
        self.evento = evento
        self.alocacoes = (
            evento.alocacoes
            .select_related('aluno')
            .exclude(status=AlocacaoPresenca.Status.DISPENSADO)
            .order_by('aluno__nome')
        )

        for alocacao in self.alocacoes:
            field_name = f'aluno_{alocacao.aluno_id}'
            self.fields[field_name] = forms.BooleanField(
                required=False,
                label=alocacao.aluno.nome,
                initial=(alocacao.status == AlocacaoPresenca.Status.PRESENTE),
            )

    def save(self):
        presentes_ids = set()
        for alocacao in self.alocacoes:
            field_name = f'aluno_{alocacao.aluno_id}'
            if self.cleaned_data.get(field_name):
                presentes_ids.add(alocacao.pk)

        for alocacao in self.alocacoes:
            if alocacao.pk in presentes_ids:
                alocacao.status = AlocacaoPresenca.Status.PRESENTE
            else:
                alocacao.status = AlocacaoPresenca.Status.AUSENTE
            alocacao.save(skip_validation=True)
