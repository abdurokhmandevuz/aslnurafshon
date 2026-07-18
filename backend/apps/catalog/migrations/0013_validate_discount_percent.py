from django.core.validators import MaxValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0012_productbundle_product_related_products_bundleitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailydeal',
            name='discount_percent',
            field=models.PositiveSmallIntegerField(
                default=0,
                validators=[MaxValueValidator(99)],
                verbose_name='Chegirma (%)',
            ),
        ),
        migrations.AlterField(
            model_name='product',
            name='discount_percent',
            field=models.PositiveSmallIntegerField(
                default=0,
                validators=[MaxValueValidator(99)],
                verbose_name='Chegirma (%)',
            ),
        ),
        migrations.AlterField(
            model_name='productbundle',
            name='discount_percent',
            field=models.PositiveSmallIntegerField(
                default=0,
                validators=[MaxValueValidator(99)],
                verbose_name='Chegirma foizi',
            ),
        ),
    ]
