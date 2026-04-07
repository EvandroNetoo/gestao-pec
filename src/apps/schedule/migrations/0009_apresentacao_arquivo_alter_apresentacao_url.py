from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('schedule', '0008_apresentacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='apresentacao',
            name='arquivo',
            field=models.FileField(
                blank=True,
                upload_to='apresentacoes/',
                verbose_name='Arquivo PDF',
            ),
        ),
        migrations.AlterField(
            model_name='apresentacao',
            name='url',
            field=models.URLField(blank=True, verbose_name='URL de acesso'),
        ),
    ]
