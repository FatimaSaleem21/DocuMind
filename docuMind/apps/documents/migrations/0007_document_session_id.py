from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0006_alter_document_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="session_id",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
    ]