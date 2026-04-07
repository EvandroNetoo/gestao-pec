from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from schedule.models import Apresentacao


class Command(BaseCommand):
    help = 'Adiciona uma apresentação (PDF ou Link) via terminal.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--nome',
            required=True,
            help='Nome da apresentação.',
        )
        parser.add_argument(
            '--tipo',
            required=True,
            choices=[
                Apresentacao.Tipo.PDF,
                Apresentacao.Tipo.LINK,
                'pdf',
                'link',
            ],
            help='Tipo da apresentação: PDF ou Link.',
        )
        parser.add_argument(
            '--url',
            default='',
            help='URL da apresentação.',
        )
        parser.add_argument(
            '--arquivo',
            default='',
            help='Caminho local para um arquivo PDF.',
        )

    def handle(self, *args, **options):
        nome = options['nome'].strip()
        tipo_raw = options['tipo']
        tipo = (
            Apresentacao.Tipo.PDF
            if tipo_raw.lower() == 'pdf'
            else Apresentacao.Tipo.LINK
        )
        url = options['url'].strip()
        arquivo = options['arquivo'].strip()

        if not nome:
            raise CommandError('O campo --nome não pode ser vazio.')

        arquivo_path = Path(arquivo) if arquivo else None
        if arquivo_path and not arquivo_path.is_file():
            raise CommandError(f'Arquivo não encontrado: {arquivo}')

        apresentacao = Apresentacao(
            nome=nome,
            tipo=tipo,
            url=url,
        )
        if arquivo_path:
            with arquivo_path.open('rb') as arquivo_pdf:
                apresentacao.arquivo.save(
                    arquivo_path.name,
                    File(arquivo_pdf),
                    save=False,
                )
        try:
            apresentacao.full_clean()
            apresentacao.save()
        except ValidationError as exc:
            raise CommandError(exc.messages) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f'Apresentação criada com sucesso: {apresentacao.pk} - {apresentacao}'
            )
        )
