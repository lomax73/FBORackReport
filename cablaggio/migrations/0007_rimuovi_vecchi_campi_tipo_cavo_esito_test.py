from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cablaggio', '0006_migra_tipo_cavo_esito_test'),
    ]

    operations = [
        migrations.RemoveField(model_name='posizione', name='tipo_cavo'),
        migrations.RemoveField(model_name='posizione', name='esito_test'),
        migrations.RenameField(model_name='posizione', old_name='tipo_cavo_fk', new_name='tipo_cavo'),
        migrations.RenameField(model_name='posizione', old_name='esito_test_fk', new_name='esito_test'),
    ]
