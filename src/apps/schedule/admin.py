from django.contrib import admin

from schedule.models import (
    AlocacaoPresenca,
    Aluno,
    Evento,
    Oficina,
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
class SemestreAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome']
    inlines = [TurmaInline]


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'semestre']
    list_filter = ['semestre', 'semestre__ativo']
    search_fields = ['nome']
    inlines = [AlunoInline]


@admin.register(Oficina)
class OficinaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'local_padrao']
    search_fields = ['nome']


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'turma', 'total_presencas']
    list_filter = ['turma__semestre', 'turma']
    search_fields = ['nome']
    filter_horizontal = ['oficinas_fixas']


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
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
class AlocacaoPresencaAdmin(admin.ModelAdmin):
    list_display = ['aluno', 'evento', 'status']
    list_filter = ['status', 'evento']
    search_fields = ['aluno__nome', 'evento__titulo']
