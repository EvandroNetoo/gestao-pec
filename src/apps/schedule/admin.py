from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from schedule.models import (
    AlocacaoPresenca,
    Aluno,
    Apresentacao,
    Evento,
    Oficina,
    Professor,
    Semestre,
    Turma,
)


class TurmaInline(admin.TabularInline):
    model = Turma
    extra = 1


class AlunoInline(admin.TabularInline):
    model = Aluno
    extra = 1


class AlocacaoInline(admin.TabularInline):
    model = AlocacaoPresenca
    extra = 0
    autocomplete_fields = ['aluno']


@admin.register(Semestre)
class SemestreAdmin(ImportExportModelAdmin):
    list_display = ['nome', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome']
    inlines = [TurmaInline]


@admin.register(Turma)
class TurmaAdmin(ImportExportModelAdmin):
    list_display = ['nome', 'semestre']
    list_filter = ['semestre', 'semestre__ativo']
    search_fields = ['nome']
    inlines = [AlunoInline]


@admin.register(Oficina)
class OficinaAdmin(ImportExportModelAdmin):
    list_display = ['nome', 'local_padrao', 'total_professores']
    search_fields = ['nome']
    filter_horizontal = ['professores']

    def total_professores(self, obj):
        return obj.professores.filter(ativo=True).count()

    total_professores.short_description = 'Professores'


@admin.register(Professor)
class ProfessorAdmin(ImportExportModelAdmin):
    list_display = ['nome', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome']


@admin.register(Aluno)
class AlunoAdmin(ImportExportModelAdmin):
    list_display = ['nome', 'turma', 'total_presencas']
    list_filter = ['turma__semestre', 'turma']
    search_fields = ['nome']
    filter_horizontal = ['oficinas_fixas']


@admin.register(Evento)
class EventoAdmin(ImportExportModelAdmin):
    list_display = [
        'titulo',
        'tipo',
        'data_hora_inicio',
        'data_hora_fim',
        'peso_presenca',
        'cancelado',
    ]
    list_filter = ['tipo', 'cancelado', 'oficinas']
    search_fields = ['titulo']
    filter_horizontal = ['oficinas']
    inlines = [AlocacaoInline]


@admin.register(AlocacaoPresenca)
class AlocacaoPresencaAdmin(ImportExportModelAdmin):
    list_display = ['aluno', 'evento', 'status']
    list_filter = ['status', 'evento']
    search_fields = ['aluno__nome', 'evento__titulo']


@admin.register(Apresentacao)
class ApresentacaoAdmin(ImportExportModelAdmin):
    list_display = ['nome', 'tipo', 'url', 'arquivo', 'atualizado_em']
    list_filter = ['tipo']
    search_fields = ['nome', 'url']
