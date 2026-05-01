from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="tg_id",
            field=models.BigIntegerField(null=True, blank=True, db_index=True),
        ),
        migrations.CreateModel(
            name="CachedEvent",
            fields=[
                ("id", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("source", models.CharField(max_length=32)),
                ("url", models.URLField(blank=True, default="", max_length=1024)),
                ("title", models.CharField(max_length=512)),
                ("title_ru", models.CharField(blank=True, default="", max_length=512)),
                ("category", models.CharField(max_length=32)),
                ("date_start", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("date_end", models.DateTimeField(blank=True, null=True)),
                ("venue_name", models.CharField(blank=True, default="", max_length=256)),
                ("city", models.CharField(blank=True, default="", max_length=128)),
                ("price_from", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("price_to", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("currency", models.CharField(default="MDL", max_length=8)),
                ("is_free", models.BooleanField(default=False)),
                ("image_url", models.URLField(blank=True, default="", max_length=1024)),
                ("ticket_links", models.JSONField(blank=True, default=dict)),
                ("fetched_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Cached Event",
                "verbose_name_plural": "Cached Events",
                "db_table": "cached_events",
            },
        ),
        migrations.CreateModel(
            name="Recommendation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("user_id", models.CharField(db_index=True, max_length=64)),
                ("is_new", models.BooleanField(default=True)),
                ("rank", models.PositiveSmallIntegerField()),
                ("score", models.FloatField()),
                ("feature_breakdown", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "cached_event",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="recommendations",
                        to="api.cachedevent",
                    ),
                ),
            ],
            options={
                "verbose_name": "Recommendation",
                "verbose_name_plural": "Recommendations",
                "db_table": "recommendations",
            },
        ),
        migrations.AddConstraint(
            model_name="recommendation",
            constraint=models.UniqueConstraint(
                fields=("user_id", "cached_event"),
                name="recommendation_unique_user_event",
            ),
        ),
        migrations.AddIndex(
            model_name="recommendation",
            index=models.Index(fields=["user_id", "is_new"], name="recommendat_user_id_5dba23_idx"),
        ),
        migrations.AddIndex(
            model_name="recommendation",
            index=models.Index(fields=["user_id", "created_at"], name="recommendat_user_id_2c8a51_idx"),
        ),
    ]
