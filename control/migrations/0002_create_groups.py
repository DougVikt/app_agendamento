from django.db import migrations


def create_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for nome in ['recepcao', 'central', 'profissional']:
        Group.objects.get_or_create(name=nome)


def remove_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=['recepcao', 'central', 'profissional']).delete()


class Migration(migrations.Migration):
    dependencies = [('control', '0001_initial')]

    operations = [migrations.RunPython(create_groups, remove_groups)]