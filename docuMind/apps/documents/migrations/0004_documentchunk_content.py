from django.db import migrations, models
import django.db.models.deletion
import pgvector.django


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_document'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DocumentChunk',
        ),
        migrations.CreateModel(
            name='DocumentChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('chunk_index', models.IntegerField()),
                ('page_number', models.IntegerField()),
                ('embedding', pgvector.django.VectorField(dimensions=1536, null=True, blank=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='documents.document')),
            ],
            options={
                'ordering': ['document', 'chunk_index'],
            },
        ),
    ]