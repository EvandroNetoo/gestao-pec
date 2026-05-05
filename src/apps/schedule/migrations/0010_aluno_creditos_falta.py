from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('schedule', '0009_apresentacao_arquivo_alter_apresentacao_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='aluno',
            name='creditos_falta',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=6,
                verbose_name='Créditos de falta',
            ),
        ),
    ]
