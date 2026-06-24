from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("stocks", "0007_company_timing_signals")]

    operations = [
        migrations.AddField(model_name="scoresnapshot", name="market_validation_score", field=models.FloatField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name="scoresnapshot", name="valuation_adjustment", field=models.FloatField(default=0)),
    ]
