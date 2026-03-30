from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0038_add_consultation_record'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointmentsettings',
            name='work_start_time',
            field=models.CharField(
                default='08:00',
                help_text='Work start time in HH:MM format',
                max_length=5,
            ),
        ),
        migrations.AddField(
            model_name='appointmentsettings',
            name='work_end_time',
            field=models.CharField(
                default='18:00',
                help_text='Work end time in HH:MM format',
                max_length=5,
            ),
        ),
        migrations.AddField(
            model_name='appointmentsettings',
            name='work_days',
            field=models.JSONField(
                default=list,
                help_text='Working days list using FullCalendar convention (0=Sun,1=Mon,2=Tue,3=Wed,4=Thu,5=Fri,6=Sat)',
            ),
        ),
    ]
