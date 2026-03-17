from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0006_oficina_semestre'),
    ]

    operations = [
        migrations.CreateModel(
            name='Professor',
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
                ('nome', models.CharField(max_length=150, verbose_name='Nome')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Professor',
                'verbose_name_plural': 'Professores',
                'ordering': ['nome'],
            },
        ),
        migrations.AddField(
            model_name='oficina',
            name='professores',
            field=models.ManyToManyField(
                blank=True,
                related_name='oficinas',
                to='schedule.professor',
                verbose_name='Professores',
            ),
        ),
    ]
