from django.db import migrations, models


def deduplicate_nicknames(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    used = set(User.objects.exclude(nickname="").values_list("nickname", flat=True))
    duplicate_names = (
        User.objects.exclude(nickname="")
        .values_list("nickname", flat=True)
        .order_by("nickname")
    )
    seen = set()
    for nickname in duplicate_names:
        if nickname in seen:
            continue
        seen.add(nickname)
        users = list(User.objects.filter(nickname=nickname).order_by("id"))
        for position, user in enumerate(users[1:], start=2):
            suffix = str(position)
            candidate = f"{nickname}{suffix}"[:40]
            counter = position
            while candidate in used:
                counter += 1
                suffix = str(counter)
                candidate = f"{nickname[:40-len(suffix)]}{suffix}"
            user.nickname = candidate
            user.save(update_fields=("nickname",))
            used.add(candidate)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_user_risk_type_cleanup")]

    operations = [
        migrations.RunPython(deduplicate_nicknames, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                condition=~models.Q(nickname=""),
                fields=("nickname",),
                name="unique_nonempty_nickname",
            ),
        ),
    ]
