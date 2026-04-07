from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('schedule', '0007_professor_oficina'),
    ]

    operations = [
        migrations.CreateModel(
            name='Apresentacao',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('nome', models.CharField(max_length=200, verbose_name='Nome')),
                (
                    'tipo',
                    models.CharField(
                        choices=[('PDF', 'PDF'), ('Link', 'Link')],
                        max_length=10,
                        verbose_name='Tipo',
                    ),
                ),
                ('url', models.URLField(verbose_name='URL de acesso')),
                (
                    'criado_em',
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name='Criado em',
                    ),
                ),
                (
                    'atualizado_em',
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name='Atualizado em',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Apresentação',
                'verbose_name_plural': 'Apresentações',
                'ordering': ['nome'],
            },
        ),
    ]
