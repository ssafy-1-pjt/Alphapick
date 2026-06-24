from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("stocks", "0006_watchlistfolder_watchlist_folder")]

    operations = [
        migrations.AddField(model_name="scoresnapshot", name="action_label", field=models.CharField(default="관망", max_length=80)),
        migrations.AddField(model_name="scoresnapshot", name="action_signal", field=models.CharField(db_index=True, default="WATCH", max_length=32)),
        migrations.AddField(model_name="scoresnapshot", name="financial_data_status", field=models.CharField(default="partial", max_length=24)),
        migrations.AddField(model_name="scoresnapshot", name="is_investment_ineligible", field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name="scoresnapshot", name="red_flag_reasons", field=models.JSONField(blank=True, default=list)),
    ]
