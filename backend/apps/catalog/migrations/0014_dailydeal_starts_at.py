from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0013_validate_discount_percent'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailydeal',
            name='starts_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Boshlanish vaqti'),
        ),
    ]
