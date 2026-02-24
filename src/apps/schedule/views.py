from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db.models import (
    Case,
    Count,
    IntegerField,
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

from schedule.forms import (
    AlocarAlunosForm,
    AlunoForm,
    CopiarTurmaForm,
    EventoCriarForm,
    EventoForm,
    OficinaForm,
    PresencaForm,
    SemestreForm,
    TurmaForm,
)
from schedule.models import (
    AlocacaoPresenca,
    Aluno,
    Evento,
    Oficina,
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
            evento.alocacoes.select_related('aluno')
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

        return render(request, self.template_name, {
            'evento': evento,
            'form': form,
        })

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

        return render(request, self.template_name, {
            'evento': evento,
            'form': form,
        })


# ═══════════════════════════════════════════════════════════════════
#  DASHBOARD (login obrigatório)
# ═══════════════════════════════════════════════════════════════════


class DashboardView(TemplateView):
    template_name = 'schedule/gestao/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_turmas'] = Turma.objects.filter(
            semestre__ativo=True
        ).count()
        ctx['total_oficinas'] = Oficina.objects.count()
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
        qs = super().get_queryset().annotate(
            total_turmas=Count('turmas')
        )
        return qs


class SemestreCreateView(CreateView):
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


class SemestreUpdateView(UpdateView):
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


class TurmaCreateView(CreateView):
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


class TurmaUpdateView(UpdateView):
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
        return render(request, 'schedule/gestao/form.html', {
            'form': form,
            'page_title': f'Copiar Turma: {turma}',
            'back_url': reverse_lazy('turma_list'),
        })

    def post(self, request, pk):
        turma = get_object_or_404(Turma, pk=pk)
        form = CopiarTurmaForm(request.POST)
        if form.is_valid():
            nova = copiar_turma(
                turma, form.cleaned_data['semestre_destino']
            )
            messages.success(
                request,
                f'Turma copiada: {nova} '
                f'({nova.alunos.count()} alunos).',
            )
            return redirect('turma_list')
        return render(request, 'schedule/gestao/form.html', {
            'form': form,
            'page_title': f'Copiar Turma: {turma}',
            'back_url': reverse_lazy('turma_list'),
        })


# ═══════════════════════════════════════════════════════════════════
#  OFICINA — CRUD
# ═══════════════════════════════════════════════════════════════════


class OficinaListView(ListView):
    model = Oficina
    template_name = 'schedule/gestao/oficina_list.html'
    context_object_name = 'oficinas'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(nome__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class OficinaCreateView(CreateView):
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


class OficinaUpdateView(UpdateView):
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


class AlunoCreateView(CreateView):
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


class AlunoUpdateView(UpdateView):
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
            self.object.alocacoes.select_related('evento')
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
        qs = super().get_queryset().prefetch_related('oficinas').annotate(
            total_alocados=Count('alocacoes'),
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
        return render(request, self.template_name, {
            'form': form,
            'page_title': 'Novo Evento',
            'back_url': reverse_lazy('evento_list'),
        })

    def post(self, request):
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
            oficinas = d.get('oficinas')
            criados = 0
            for dt in datas:
                evento = Evento(
                    titulo=d['titulo'],
                    tipo=d['tipo'],
                    data_hora_inicio=datetime.combine(
                        dt, d['hora_inicio']
                    ),
                    data_hora_fim=datetime.combine(
                        dt, d['hora_fim']
                    ),
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
            return redirect('evento_list')

        return render(request, self.template_name, {
            'form': form,
            'page_title': 'Novo Evento',
            'back_url': reverse_lazy('evento_list'),
        })


class EventoUpdateView(UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = 'schedule/gestao/form.html'
    success_url = reverse_lazy('evento_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'Editar Evento: {self.object}'
        ctx['back_url'] = self.success_url
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Evento atualizado com sucesso.')
        return super().form_valid(form)


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
        ctx['alocacoes'] = (
            self.object.alocacoes.select_related('aluno')
            .order_by('aluno__nome')
        )
        return ctx


class EventoAlocarView(View):
    """Aloca múltiplos alunos a um evento."""

    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        form = AlocarAlunosForm(evento=evento)
        return render(request, 'schedule/gestao/form.html', {
            'form': form,
            'page_title': f'Alocar Alunos — {evento.titulo}',
            'back_url': reverse_lazy(
                'evento_detail_gestao', kwargs={'pk': pk}
            ),
        })

    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        form = AlocarAlunosForm(request.POST, evento=evento)
        if form.is_valid():
            alunos = form.cleaned_data['alunos']
            criados = 0
            erros = []
            for aluno in alunos:
                aloc = AlocacaoPresenca(
                    evento=evento,
                    aluno=aluno,
                    status=AlocacaoPresenca.Status.PREVISTO,
                )
                try:
                    aloc.save()
                    criados += 1
                except Exception as e:
                    erros.append(f'{aluno.nome}: {e}')
            if criados:
                messages.success(
                    request,
                    f'{criados} aluno(s) alocado(s) com sucesso.',
                )
            for erro in erros:
                messages.error(request, erro)
            return redirect('evento_detail_gestao', pk=pk)
        return render(request, 'schedule/gestao/form.html', {
            'form': form,
            'page_title': f'Alocar Alunos — {evento.titulo}',
            'back_url': reverse_lazy(
                'evento_detail_gestao', kwargs={'pk': pk}
            ),
        })


class AlocacaoRemoverView(View):
    """Remove uma alocação de um evento (HTMX)."""

    def post(self, request, pk):
        alocacao = get_object_or_404(
            AlocacaoPresenca.objects.select_related('evento'), pk=pk
        )
        evento_pk = alocacao.evento.pk
        alocacao.delete()
        messages.success(request, 'Alocação removida.')
        return redirect('evento_detail_gestao', pk=evento_pk)


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


# ═══════════════════════════════════════════════════════════════════
#  RELATÓRIOS
# ═══════════════════════════════════════════════════════════════════


class RelatorioPresencaTurmaView(ListView):
    """Relatório de presenças agrupado por turma."""

    template_name = 'schedule/relatorios/presenca_turma.html'
    context_object_name = 'turmas'

    def get_queryset(self):
        return Turma.objects.filter(
            semestre__ativo=True
        ).select_related('semestre').prefetch_related('alunos').order_by(
            '-semestre__nome', 'nome'
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
        return Evento.objects.filter(cancelado=False).annotate(
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
        ).order_by('-data_hora_inicio')

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
            self.object.alocacoes.select_related('evento')
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
            'percentual': (
                round(presentes * 100 / total) if total else 0
            ),
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
        ctx['total_oficinas'] = Oficina.objects.count()
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
            Evento.objects.filter(cancelado=False)
            .values('tipo')
            .annotate(total=Count('pk'))
            .order_by('tipo')
        )

        ctx['top_alunos'] = (
            Aluno.objects.filter(
                turma__semestre__ativo=True,
            ).annotate(
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
