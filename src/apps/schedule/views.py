from datetime import datetime, timedelta
from time import sleep

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import (
    Case,
    Count,
    IntegerField,
    Prefetch,
    Q,
    Sum,
    Value,
    When,
)
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from django_htmx.http import HttpResponseClientRedirect

from core.mixins import HtmxFormViewMixin
from schedule.forms import (
    AlocarAlunosForm,
    AlunoBulkForm,
    AlunoForm,
    ApresentacaoForm,
    CopiarTurmaForm,
    EventoCriarForm,
    EventoForm,
    OficinaBulkForm,
    OficinaForm,
    PresencaForm,
    SemestreForm,
    TurmaForm,
)
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
from schedule.services import copiar_turma

# ═══════════════════════════════════════════════════════════════════
#  VIEWS PÚBLICAS (sem login)
# ═══════════════════════════════════════════════════════════════════


@method_decorator(login_not_required, name='dispatch')
class AgendaView(TemplateView):
    template_name = 'schedule/agenda.html'


@method_decorator(login_not_required, name='dispatch')
class EventosApiView(View):
    """Retorna eventos no formato esperado pelo FullCalendar."""

    def get(self, request):
        eventos = Evento.objects.prefetch_related('oficinas').filter(
            cancelado=False,
        )

        start = request.GET.get('start')
        end = request.GET.get('end')
        if start and end:
            eventos = eventos.filter(
                data_hora_inicio__gte=start,
                data_hora_fim__lte=end,
            )

        data = []
        for evento in eventos:
            cor = {
                Evento.Tipo.PERIODICO: '#2563eb',
                Evento.Tipo.ESPORADICO: '#c90c0f',
            }.get(evento.tipo, '#6b7280')

            data.append({
                'id': evento.pk,
                'title': evento.titulo,
                'start': evento.data_hora_inicio.isoformat(),
                'end': evento.data_hora_fim.isoformat(),
                'color': cor,
                'extendedProps': {
                    'tipo': evento.tipo,
                    'local': evento.get_local_definitivo(),
                },
            })

        return JsonResponse(data, safe=False)


@method_decorator(login_not_required, name='dispatch')
class EventoDetalhesView(TemplateView):
    """Retorna fragmento HTML com detalhes do evento (para modal HTMX)."""

    template_name = 'schedule/partials/evento_detalhes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento = get_object_or_404(
            Evento.objects.prefetch_related('oficinas'),
            pk=kwargs['pk'],
        )
        alocacoes = (
            evento.alocacoes
            .select_related('aluno')
            .filter(
                status__in=[
                    AlocacaoPresenca.Status.PREVISTO,
                    AlocacaoPresenca.Status.PRESENTE,
                ]
            )
            .order_by('aluno__nome')
        )
        context['evento'] = evento
        context['alocacoes'] = alocacoes
        return context


@method_decorator(login_not_required, name='dispatch')
class PresencaView(View):
    """Formulário público para registrar presenças."""

    template_name = 'schedule/presenca.html'
    template_sucesso = 'schedule/partials/presenca_sucesso.html'

    def get_evento(self, pk):
        return get_object_or_404(Evento, pk=pk, cancelado=False)

    def get(self, request, pk):
        evento = self.get_evento(pk)
        form = PresencaForm(evento=evento)

        return render(
            request,
            self.template_name,
            {
                'evento': evento,
                'form': form,
            },
        )

    def post(self, request, pk):
        evento = self.get_evento(pk)
        form = PresencaForm(request.POST, evento=evento)

        if form.is_valid():
            form.save()
            return render(
                request,
                self.template_sucesso,
                {'evento': evento},
            )

        return render(
            request,
            self.template_name,
            {
                'evento': evento,
                'form': form,
            },
        )


@method_decorator(login_not_required, name='dispatch')
class DivisaoGruposView(TemplateView):
    template_name = 'schedule/divisao_grupos.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        professor_id = self.request.GET.get('professor', '').strip()

        oficinas_qs = (
            Oficina.objects
            .select_related('semestre')
            .filter(semestre__ativo=True)
            .prefetch_related(
                'professores',
                Prefetch(
                    'alunos',
                    queryset=Aluno.objects.select_related('turma').filter(
                        turma__semestre__ativo=True
                    ),
                ),
            )
            .annotate(
                total_alunos=Count(
                    'alunos',
                    filter=Q(alunos__turma__semestre__ativo=True),
                    distinct=True,
                ),
                total_professores=Count(
                    'professores',
                    filter=Q(professores__ativo=True),
                    distinct=True,
                ),
            )
            .order_by('nome')
        )

        if professor_id:
            oficinas_qs = oficinas_qs.filter(
                professores__id=professor_id,
                professores__ativo=True,
            )

        professores = Professor.objects.filter(ativo=True).order_by('nome')
        total_alunos = (
            oficinas_qs.aggregate(total=Sum('total_alunos'))['total'] or 0
        )
        total_oficinas = oficinas_qs.count()
        total_professores = (
            Professor.objects
            .filter(ativo=True, oficinas__in=oficinas_qs)
            .distinct()
            .count()
        )

        ctx['oficinas'] = oficinas_qs
        ctx['professores'] = professores
        ctx['professor_filtro'] = professor_id
        ctx['total_alunos'] = total_alunos
        ctx['total_oficinas'] = total_oficinas
        ctx['total_professores'] = total_professores
        return ctx


@method_decorator(login_not_required, name='dispatch')
class ApresentacaoListView(ListView):
    model = Apresentacao
    template_name = 'schedule/apresentacoes.html'
    context_object_name = 'apresentacoes'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tipos_apresentacao'] = Apresentacao.Tipo.choices
        return ctx


class StaffRequiredMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff


class ApresentacaoCreateView(StaffRequiredMixin, CreateView):
    model = Apresentacao
    form_class = ApresentacaoForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('apresentacao_list')

    def get(self, request, *args, **kwargs):
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Nova Apresentação'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Apresentação criada com sucesso.')
        return super().form_valid(form)

    def form_invalid(self, form):
        for errors in form.errors.values():
            for error in errors:
                messages.error(self.request, error)
        return redirect(self.success_url)


class ApresentacaoUpdateView(StaffRequiredMixin, UpdateView):
    model = Apresentacao
    form_class = ApresentacaoForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('apresentacao_list')

    def get(self, request, *args, **kwargs):
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Editar Apresentação: {self.object.nome}'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Apresentação atualizada com sucesso.')
        return super().form_valid(form)

    def form_invalid(self, form):
        for errors in form.errors.values():
            for error in errors:
                messages.error(self.request, error)
        return redirect(self.success_url)


class ApresentacaoDeleteView(StaffRequiredMixin, DeleteView):
    model = Apresentacao
    template_name = 'schedule/gestao/confirm_delete.html'
    success_url = reverse_lazy('apresentacao_list')
    context_object_name = 'obj'

    def get(self, request, *args, **kwargs):
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Excluir Apresentação'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Apresentação excluída com sucesso.')
        return super().form_valid(form)


# ═══════════════════════════════════════════════════════════════════
#  DASHBOARD (login obrigatório)
# ═══════════════════════════════════════════════════════════════════


class DashboardView(TemplateView):
    template_name = 'schedule/gestao/dashboard.html'

    def get_context_data(self, **kwargs):
        sleep(0.5)
        ctx = super().get_context_data(**kwargs)
        ctx['total_turmas'] = Turma.objects.filter(
            semestre__ativo=True
        ).count()
        ctx['total_oficinas'] = Oficina.objects.filter(
            semestre__ativo=True
        ).count()
        ctx['total_alunos'] = Aluno.objects.filter(
            turma__semestre__ativo=True
        ).count()
        ctx['total_eventos'] = Evento.objects.filter(
            cancelado=False,
        ).count()
        ctx['proximos_eventos'] = Evento.objects.filter(
            cancelado=False,
        ).order_by('data_hora_inicio')[:5]
        return ctx


# ═══════════════════════════════════════════════════════════════════
#  SEMESTRE — CRUD
# ═══════════════════════════════════════════════════════════════════


class SemestreListView(ListView):
    model = Semestre
    template_name = 'schedule/gestao/semestre_list.html'
    context_object_name = 'semestres'

    def get_queryset(self):
        qs = super().get_queryset().annotate(total_turmas=Count('turmas'))
        return qs


class SemestreCreateView(HtmxFormViewMixin, CreateView):
    model = Semestre
    form_class = SemestreForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('semestre_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Novo Semestre'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Semestre criado com sucesso.')
        return super().form_valid(form)


class SemestreUpdateView(HtmxFormViewMixin, UpdateView):
    model = Semestre
    form_class = SemestreForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('semestre_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Editar Semestre: {self.object}'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Semestre atualizado com sucesso.')
        return super().form_valid(form)


class SemestreDeleteView(DeleteView):
    model = Semestre
    template_name = 'schedule/gestao/confirm_delete.html'
    success_url = reverse_lazy('semestre_list')
    context_object_name = 'obj'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Excluir Semestre'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Semestre excluído com sucesso.')
        return super().form_valid(form)


# ═══════════════════════════════════════════════════════════════════
#  TURMA — CRUD
# ═══════════════════════════════════════════════════════════════════


class TurmaListView(ListView):
    model = Turma
    template_name = 'schedule/gestao/turma_list.html'
    context_object_name = 'turmas'

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related('semestre')
            .annotate(total_alunos=Count('alunos'))
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(nome__icontains=q)
        semestre = self.request.GET.get('semestre')
        if semestre:
            qs = qs.filter(semestre_id=semestre)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['semestre_filtro'] = self.request.GET.get('semestre', '')
        ctx['semestres'] = Semestre.objects.all()
        return ctx


class TurmaCreateView(HtmxFormViewMixin, CreateView):
    model = Turma
    form_class = TurmaForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('turma_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Nova Turma'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Turma criada com sucesso.')
        return super().form_valid(form)


class TurmaUpdateView(HtmxFormViewMixin, UpdateView):
    model = Turma
    form_class = TurmaForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('turma_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Editar Turma: {self.object}'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Turma atualizada com sucesso.')
        return super().form_valid(form)


class TurmaDeleteView(DeleteView):
    model = Turma
    template_name = 'schedule/gestao/confirm_delete.html'
    success_url = reverse_lazy('turma_list')
    context_object_name = 'obj'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Excluir Turma'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Turma excluída com sucesso.')
        return super().form_valid(form)


class TurmaCopiarView(View):
    """Copia uma turma e seus alunos para um novo semestre."""

    def get(self, request, pk):
        turma = get_object_or_404(Turma, pk=pk)
        form = CopiarTurmaForm()
        return render(
            request,
            'schedule/gestao/form.html',
            {
                'form': form,
                'page_title': f'Copiar Turma: {turma}',
                'back_url': reverse_lazy('turma_list'),
            },
        )

    def post(self, request, pk):
        turma = get_object_or_404(Turma, pk=pk)
        form = CopiarTurmaForm(request.POST)
        if form.is_valid():
            nova = copiar_turma(turma, form.cleaned_data['semestre_destino'])
            messages.success(
                request,
                f'Turma copiada: {nova} ({nova.alunos.count()} alunos).',
            )
            return HttpResponseClientRedirect(str(reverse_lazy('turma_list')))
        return render(
            request,
            'components/django_form/index.html',
            {'form': form},
        )


# ═══════════════════════════════════════════════════════════════════
#  OFICINA — CRUD
# ═══════════════════════════════════════════════════════════════════


class OficinaListView(ListView):
    model = Oficina
    template_name = 'schedule/gestao/oficina_list.html'
    context_object_name = 'oficinas'

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related('semestre')
            .filter(semestre__ativo=True)
            .annotate(
                total_alunos=Count(
                    'alunos',
                    filter=Q(alunos__turma__semestre__ativo=True),
                    distinct=True,
                ),
                total_professores=Count(
                    'professores',
                    filter=Q(professores__ativo=True),
                    distinct=True,
                ),
            )
            .order_by('nome')
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(nome__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class OficinaCreateView(HtmxFormViewMixin, CreateView):
    model = Oficina
    form_class = OficinaForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('oficina_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Nova Oficina'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Oficina criada com sucesso.')
        return super().form_valid(form)


class OficinaUpdateView(HtmxFormViewMixin, UpdateView):
    model = Oficina
    form_class = OficinaForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('oficina_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Editar Oficina: {self.object}'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        # A sincronização de alocações em eventos futuros é feita
        # automaticamente pelo signal m2m_changed em Aluno.oficinas_fixas.
        messages.success(self.request, 'Oficina atualizada com sucesso.')
        return super().form_valid(form)


class OficinaDeleteView(DeleteView):
    model = Oficina
    template_name = 'schedule/gestao/confirm_delete.html'
    success_url = reverse_lazy('oficina_list')
    context_object_name = 'obj'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Excluir Oficina'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Oficina excluída com sucesso.')
        return super().form_valid(form)


class OficinaBulkCreateView(View):
    """Adicionar várias oficinas de uma vez."""

    template_name = 'schedule/gestao/oficina_bulk.html'
    success_url = reverse_lazy('oficina_list')

    def get(self, request):
        form = OficinaBulkForm()
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'page_title': 'Adicionar Oficinas em Lote',
                'back_url': self.success_url,
            },
        )

    def post(self, request):
        form = OficinaBulkForm(request.POST)
        if form.is_valid():
            semestre = form.cleaned_data['semestre']
            oficinas_data = form.cleaned_data['oficinas']
            oficinas = [
                Oficina(
                    nome=item['nome'],
                    local_padrao=item['local_padrao'],
                    semestre=semestre,
                )
                for item in oficinas_data
            ]
            Oficina.objects.bulk_create(oficinas)
            messages.success(
                request,
                f'{len(oficinas)} oficina(s) adicionada(s) ao semestre {semestre}.',
            )
            return HttpResponseClientRedirect(str(self.success_url))
        return render(
            request,
            'components/django_form/index.html',
            {'form': form},
        )


# ═══════════════════════════════════════════════════════════════════
#  ALUNO — CRUD
# ═══════════════════════════════════════════════════════════════════


class AlunoListView(ListView):
    model = Aluno
    template_name = 'schedule/gestao/aluno_list.html'
    context_object_name = 'alunos'

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related('turma', 'turma__semestre')
            .prefetch_related('oficinas_fixas')
            .filter(turma__semestre__ativo=True)
            .annotate(
                total_presencas=Sum(
                    Case(
                        When(
                            alocacoes__status=AlocacaoPresenca.Status.PRESENTE,
                            alocacoes__evento__cancelado=False,
                            then='alocacoes__evento__peso_presenca',
                        ),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ),
            )
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(nome__icontains=q)
        turma = self.request.GET.get('turma')
        if turma:
            qs = qs.filter(turma_id=turma)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['turma_filtro'] = self.request.GET.get('turma', '')
        ctx['turmas'] = Turma.objects.filter(
            semestre__ativo=True
        ).select_related('semestre')
        return ctx


class AlunoCreateView(HtmxFormViewMixin, CreateView):
    model = Aluno
    form_class = AlunoForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('aluno_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Novo Aluno'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Aluno criado com sucesso.')
        return super().form_valid(form)


class AlunoUpdateView(HtmxFormViewMixin, UpdateView):
    model = Aluno
    form_class = AlunoForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('aluno_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Editar Aluno: {self.object}'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Aluno atualizado com sucesso.')
        return super().form_valid(form)


class AlunoDeleteView(DeleteView):
    model = Aluno
    template_name = 'schedule/gestao/confirm_delete.html'
    success_url = reverse_lazy('aluno_list')
    context_object_name = 'obj'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Excluir Aluno'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Aluno excluído com sucesso.')
        return super().form_valid(form)


class AlunoBulkCreateView(View):
    """Adicionar vários alunos de uma vez."""

    template_name = 'schedule/gestao/aluno_bulk.html'
    success_url = reverse_lazy('aluno_list')

    def get(self, request):
        form = AlunoBulkForm()
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'page_title': 'Adicionar Alunos em Lote',
                'back_url': self.success_url,
            },
        )

    def post(self, request):
        form = AlunoBulkForm(request.POST)
        if form.is_valid():
            turma = form.cleaned_data['turma']
            nomes = form.cleaned_data['nomes']
            alunos = [Aluno(nome=nome, turma=turma) for nome in nomes]
            Aluno.objects.bulk_create(alunos)
            messages.success(
                request,
                f'{len(alunos)} aluno(s) adicionado(s) à turma {turma}.',
            )
            return HttpResponseClientRedirect(str(self.success_url))
        return render(
            request,
            'components/django_form/index.html',
            {'form': form},
        )


class AlunoDetailView(DetailView):
    model = Aluno
    template_name = 'schedule/gestao/aluno_detail.html'
    context_object_name = 'aluno'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('turma')
            .prefetch_related('oficinas_fixas')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['alocacoes'] = (
            self.object.alocacoes
            .select_related('evento')
            .filter(evento__cancelado=False)
            .order_by('-evento__data_hora_inicio')
        )
        return ctx


# ═══════════════════════════════════════════════════════════════════
#  EVENTO — CRUD
# ═══════════════════════════════════════════════════════════════════


class EventoListView(ListView):
    model = Evento
    template_name = 'schedule/gestao/evento_list.html'
    context_object_name = 'eventos'

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .prefetch_related('oficinas')
            .annotate(
                total_alocados=Count('alocacoes'),
            )
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(titulo__icontains=q)
        tipo = self.request.GET.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['tipo_filtro'] = self.request.GET.get('tipo', '')
        ctx['tipos'] = Evento.Tipo.choices
        return ctx


class EventoCreateView(View):
    """Cria evento(s) — com suporte a recorrência para periódicos."""

    template_name = 'schedule/gestao/evento_criar.html'

    def get(self, request):
        form = EventoCriarForm()
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'page_title': 'Novo Evento',
                'back_url': reverse_lazy('evento_list'),
            },
        )

    def post(self, request):
        from django.utils import timezone

        form = EventoCriarForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data

            # Gerar lista de datas
            datas = [d['data']]

            if d['tipo'] == Evento.Tipo.PERIODICO:
                periodo = d['periodo']
                if periodo == 'semanal':
                    intervalo = 7
                elif periodo == 'quinzenal':
                    intervalo = 14
                else:
                    intervalo = d['intervalo_dias']

                current = d['data'] + timedelta(days=intervalo)
                while current <= d['data_fim_recorrencia']:
                    datas.append(current)
                    current += timedelta(days=intervalo)

            # Criar eventos
            # A alocação de alunos é feita automaticamente pelo signal
            # m2m_changed em Evento.oficinas ao chamar evento.oficinas.set().
            oficinas = d.get('oficinas')
            criados = 0
            tz = timezone.get_current_timezone()
            for dt in datas:
                data_hora_inicio = timezone.make_aware(
                    datetime.combine(dt, d['hora_inicio']),
                    tz,
                )
                data_hora_fim = timezone.make_aware(
                    datetime.combine(dt, d['hora_fim']),
                    tz,
                )
                evento = Evento(
                    titulo=d['titulo'],
                    tipo=d['tipo'],
                    data_hora_inicio=data_hora_inicio,
                    data_hora_fim=data_hora_fim,
                    local=d.get('local', '') or '',
                    peso_presenca=d['peso_presenca'],
                )
                evento.save()
                if oficinas:
                    evento.oficinas.set(oficinas)
                criados += 1

            messages.success(
                request,
                f'{criados} evento(s) criado(s) com sucesso.',
            )
            return HttpResponseClientRedirect(str(reverse_lazy('evento_list')))

        return render(
            request,
            'schedule/gestao/evento_criar_form.html',
            {'form': form},
        )


class EventoUpdateView(HtmxFormViewMixin, UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('evento_list')

    def _count_futuros(self, titulo):
        from django.utils import timezone

        return (
            Evento.objects
            .filter(
                titulo=titulo,
                data_hora_inicio__gt=timezone.now(),
            )
            .exclude(pk=self.object.pk)
            .count()
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['total_futuros'] = self._count_futuros(self.object.titulo)
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Editar Evento: {self.object}'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        from django.utils import timezone

        titulo_original = self.object.titulo
        aplicar_futuros = form.cleaned_data.get('aplicar_futuros', False)

        # Salva o evento. O signal m2m_changed em Evento.oficinas sincroniza
        # automaticamente as alocações quando as oficinas mudam.
        response = super().form_valid(form)

        if aplicar_futuros:
            nova_hora_inicio = form.cleaned_data['data_hora_inicio'].time()
            nova_hora_fim = form.cleaned_data['data_hora_fim'].time()
            novo_titulo = form.cleaned_data['titulo']
            novo_tipo = form.cleaned_data['tipo']
            novo_local = form.cleaned_data.get('local') or ''
            novo_peso = form.cleaned_data['peso_presenca']
            novo_cancelado = form.cleaned_data.get('cancelado', False)
            novas_oficinas = form.cleaned_data.get('oficinas')

            futuros = list(
                Evento.objects.filter(
                    titulo=titulo_original,
                    data_hora_inicio__gt=timezone.now(),
                ).exclude(pk=self.object.pk)
            )

            for futuro in futuros:
                futuro.titulo = novo_titulo
                futuro.tipo = novo_tipo
                futuro.local = novo_local
                futuro.peso_presenca = novo_peso
                futuro.cancelado = novo_cancelado
                futuro.data_hora_inicio = futuro.data_hora_inicio.replace(
                    hour=nova_hora_inicio.hour,
                    minute=nova_hora_inicio.minute,
                    second=0,
                    microsecond=0,
                )
                futuro.data_hora_fim = futuro.data_hora_fim.replace(
                    hour=nova_hora_fim.hour,
                    minute=nova_hora_fim.minute,
                    second=0,
                    microsecond=0,
                )
                futuro.save()
                # O signal m2m_changed sincroniza as alocações ao set().
                if novas_oficinas is not None:
                    futuro.oficinas.set(novas_oficinas)

            if futuros:
                messages.info(
                    self.request,
                    f'{len(futuros)} evento(s) futuro(s) também atualizado(s).',
                )

        messages.success(self.request, 'Evento atualizado com sucesso.')
        return response


class EventoDeleteView(DeleteView):
    model = Evento
    template_name = 'schedule/gestao/confirm_delete.html'
    success_url = reverse_lazy('evento_list')
    context_object_name = 'obj'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Excluir Evento'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Evento excluído com sucesso.')
        return super().form_valid(form)


class EventoDetailView(DetailView):
    model = Evento
    template_name = 'schedule/gestao/evento_detail.html'
    context_object_name = 'evento'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('oficinas')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['alocacoes'] = self.object.alocacoes.select_related(
            'aluno'
        ).order_by('aluno__nome')
        return ctx


class EventoAlocarView(View):
    """Página de gerenciamento de alunos de um evento (add + remove)."""

    template_name = 'schedule/gestao/evento_alunos.html'

    def _context(self, evento, form):
        alocacoes = evento.alocacoes.select_related(
            'aluno', 'aluno__turma'
        ).order_by('aluno__turma__nome', 'aluno__nome')
        from django.utils import timezone

        total_futuros = (
            Evento.objects
            .filter(
                titulo=evento.titulo,
                data_hora_inicio__gt=timezone.now(),
            )
            .exclude(pk=evento.pk)
            .count()
        )
        return {
            'evento': evento,
            'form': form,
            'alocacoes': alocacoes,
            'total_futuros': total_futuros,
        }

    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        form = AlocarAlunosForm(evento=evento)
        return render(request, self.template_name, self._context(evento, form))

    def post(self, request, pk):
        from django.utils import timezone

        evento = get_object_or_404(Evento, pk=pk)
        form = AlocarAlunosForm(request.POST, evento=evento)
        if form.is_valid():
            alunos = list(form.cleaned_data['alunos'])
            propagar_futuros = request.POST.get('propagar_futuros') == '1'

            # Eventos em que aplicar (sempre este + futuros se solicitado)
            eventos_alvo = [evento]
            if propagar_futuros:
                eventos_alvo += list(
                    Evento.objects.filter(
                        titulo=evento.titulo,
                        data_hora_inicio__gt=timezone.now(),
                    ).exclude(pk=evento.pk)
                )

            criados = 0
            erros = []
            for ev in eventos_alvo:
                ja_alocados = set(
                    ev.alocacoes.values_list('aluno_id', flat=True)
                )
                for aluno in alunos:
                    if aluno.pk in ja_alocados:
                        continue
                    aloc = AlocacaoPresenca(
                        evento=ev,
                        aluno=aluno,
                        status=AlocacaoPresenca.Status.PREVISTO,
                    )
                    try:
                        aloc.save()
                        criados += 1
                    except Exception as e:
                        if ev.pk == evento.pk:
                            erros.append(f'{aluno.nome}: {e}')
            if criados:
                messages.success(
                    request,
                    f'{criados} alocação(iões) criada(s)'
                    + (
                        f' em {len(eventos_alvo)} evento(s).'
                        if propagar_futuros
                        else '.'
                    ),
                )
            for erro in erros:
                messages.error(request, erro)
            return redirect('evento_alocar', pk=pk)
        return render(request, self.template_name, self._context(evento, form))


class AlocacaoRemoverView(View):
    """Remove uma alocação de um evento."""

    def post(self, request, pk):
        from django.utils import timezone

        alocacao = get_object_or_404(
            AlocacaoPresenca.objects.select_related('evento', 'aluno'),
            pk=pk,
        )
        evento = alocacao.evento
        aluno = alocacao.aluno
        propagar_futuros = request.POST.get('propagar_futuros') == '1'
        alocacao.delete()

        if propagar_futuros:
            # Remove alocações Previsto do mesmo aluno em eventos futuros
            # com o mesmo título
            removidos, _ = AlocacaoPresenca.objects.filter(
                aluno=aluno,
                evento__titulo=evento.titulo,
                evento__data_hora_inicio__gt=timezone.now(),
                status=AlocacaoPresenca.Status.PREVISTO,
            ).delete()
            messages.success(
                request,
                f'Alocação removida e propagada para {removidos} evento(s) futuro(s).',
            )
        else:
            messages.success(request, 'Alocação removida.')

        next_url = request.POST.get('next', '')
        if next_url == 'alunos':
            return redirect('evento_alocar', pk=evento.pk)
        return redirect('evento_detail_gestao', pk=evento.pk)


class EventoCancelarView(View):
    """Alterna o estado cancelado de um evento."""

    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        evento.cancelado = not evento.cancelado
        evento.save(update_fields=['cancelado'])
        if evento.cancelado:
            messages.warning(request, f'Evento "{evento}" cancelado.')
        else:
            messages.success(request, f'Evento "{evento}" restaurado.')
        return redirect('evento_detail_gestao', pk=pk)


class EventoExcluirFuturosView(View):
    """Exclui todos os eventos futuros com o mesmo título que o evento dado."""

    def post(self, request, pk):
        from django.utils import timezone

        evento = get_object_or_404(Evento, pk=pk)
        agora = timezone.now()
        futuros = Evento.objects.filter(
            titulo=evento.titulo,
            data_hora_inicio__gt=agora,
        ).exclude(pk=pk)
        total = futuros.count()
        futuros.delete()
        messages.warning(
            request,
            f'{total} evento(s) futuro(s) com o título "{evento.titulo}" excluído(s).',
        )
        return redirect('evento_detail_gestao', pk=pk)


# ═══════════════════════════════════════════════════════════════════
#  RELATÓRIOS
# ═══════════════════════════════════════════════════════════════════


class RelatorioPresencaTurmaView(ListView):
    """Relatório de presenças agrupado por turma."""

    template_name = 'schedule/relatorios/presenca_turma.html'
    context_object_name = 'turmas'

    def get_queryset(self):
        return (
            Turma.objects
            .filter(semestre__ativo=True)
            .select_related('semestre')
            .prefetch_related('alunos')
            .order_by('-semestre__nome', 'nome')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        turma_id = self.request.GET.get('turma')
        ctx['turma_filtro'] = turma_id or ''
        ctx['turmas_opcoes'] = Turma.objects.filter(
            semestre__ativo=True
        ).select_related('semestre')

        if turma_id:
            turma = get_object_or_404(Turma, pk=turma_id)
            alunos = turma.alunos.all()
            dados = []
            for aluno in alunos:
                total_p = aluno.total_presencas()
                total_alocacoes = aluno.alocacoes.filter(
                    evento__cancelado=False,
                ).count()
                total_presentes = aluno.alocacoes.filter(
                    evento__cancelado=False,
                    status=AlocacaoPresenca.Status.PRESENTE,
                ).count()
                total_ausentes = aluno.alocacoes.filter(
                    evento__cancelado=False,
                    status=AlocacaoPresenca.Status.AUSENTE,
                ).count()
                dados.append({
                    'aluno': aluno,
                    'total_presencas': total_p,
                    'total_alocacoes': total_alocacoes,
                    'presentes': total_presentes,
                    'ausentes': total_ausentes,
                    'percentual': (
                        round(total_presentes * 100 / total_alocacoes)
                        if total_alocacoes
                        else 0
                    ),
                })
            ctx['turma_selecionada'] = turma
            ctx['dados_alunos'] = dados
        return ctx


class RelatorioPresencaEventoView(ListView):
    """Relatório de presenças por evento."""

    template_name = 'schedule/relatorios/presenca_evento.html'
    context_object_name = 'eventos'

    def get_queryset(self):
        return (
            Evento.objects
            .filter(cancelado=False)
            .annotate(
                total_alocados=Count('alocacoes'),
                total_presentes=Count(
                    Case(
                        When(
                            alocacoes__status=AlocacaoPresenca.Status.PRESENTE,
                            then=Value(1),
                        ),
                        output_field=IntegerField(),
                    )
                ),
                total_ausentes=Count(
                    Case(
                        When(
                            alocacoes__status=AlocacaoPresenca.Status.AUSENTE,
                            then=Value(1),
                        ),
                        output_field=IntegerField(),
                    )
                ),
            )
            .order_by('-data_hora_inicio')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tipo = self.request.GET.get('tipo', '')
        ctx['tipo_filtro'] = tipo
        ctx['tipos'] = Evento.Tipo.choices
        if tipo:
            ctx['eventos'] = ctx['eventos'].filter(tipo=tipo)
        return ctx


class RelatorioPresencaAlunoView(DetailView):
    """Relatório detalhado de um aluno específico."""

    model = Aluno
    template_name = 'schedule/relatorios/presenca_aluno.html'
    context_object_name = 'aluno'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        alocacoes = (
            self.object.alocacoes
            .select_related('evento')
            .filter(evento__cancelado=False)
            .order_by('-evento__data_hora_inicio')
        )
        ctx['alocacoes'] = alocacoes
        total = alocacoes.count()
        presentes = alocacoes.filter(
            status=AlocacaoPresenca.Status.PRESENTE
        ).count()
        ausentes = alocacoes.filter(
            status=AlocacaoPresenca.Status.AUSENTE
        ).count()
        dispensados = alocacoes.filter(
            status=AlocacaoPresenca.Status.DISPENSADO
        ).count()
        ctx['stats'] = {
            'total': total,
            'presentes': presentes,
            'ausentes': ausentes,
            'dispensados': dispensados,
            'pontos': self.object.total_presencas(),
            'percentual': (round(presentes * 100 / total) if total else 0),
        }
        return ctx


class RelatorioGeralView(TemplateView):
    """Relatório geral / resumo do sistema."""

    template_name = 'schedule/relatorios/geral.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx['total_turmas'] = Turma.objects.filter(
            semestre__ativo=True
        ).count()
        ctx['total_oficinas'] = Oficina.objects.filter(
            semestre__ativo=True
        ).count()
        ctx['total_alunos'] = Aluno.objects.filter(
            turma__semestre__ativo=True
        ).count()
        ctx['total_eventos'] = Evento.objects.filter(
            cancelado=False,
        ).count()
        ctx['total_alocacoes'] = AlocacaoPresenca.objects.filter(
            evento__cancelado=False,
            aluno__turma__semestre__ativo=True,
        ).count()

        ctx['total_presentes'] = AlocacaoPresenca.objects.filter(
            evento__cancelado=False,
            aluno__turma__semestre__ativo=True,
            status=AlocacaoPresenca.Status.PRESENTE,
        ).count()
        ctx['total_ausentes'] = AlocacaoPresenca.objects.filter(
            evento__cancelado=False,
            aluno__turma__semestre__ativo=True,
            status=AlocacaoPresenca.Status.AUSENTE,
        ).count()

        total = ctx['total_alocacoes']
        ctx['percentual_presenca'] = (
            round(ctx['total_presentes'] * 100 / total) if total else 0
        )

        ctx['eventos_por_tipo'] = (
            Evento.objects
            .filter(cancelado=False)
            .values('tipo')
            .annotate(total=Count('pk'))
            .order_by('tipo')
        )

        ctx['top_alunos'] = (
            Aluno.objects
            .filter(
                turma__semestre__ativo=True,
            )
            .annotate(
                pontos=Sum(
                    Case(
                        When(
                            alocacoes__status=AlocacaoPresenca.Status.PRESENTE,
                            alocacoes__evento__cancelado=False,
                            then='alocacoes__evento__peso_presenca',
                        ),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
            )
            .order_by('-pontos')[:10]
        )

        return ctx
