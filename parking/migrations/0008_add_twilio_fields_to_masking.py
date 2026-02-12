# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parking', '0007_alter_vehiclecontact_relation'),
    ]

    operations = [
        migrations.AddField(
            model_name='phonenumbermasking',
            name='scanner_phone',
            field=models.CharField(blank=True, help_text="Scanner's phone number (for Twilio connection)", max_length=17, null=True),
        ),
        migrations.AddField(
            model_name='phonenumbermasking',
            name='twilio_call_sid',
            field=models.CharField(blank=True, help_text='Twilio Call SID for tracking', max_length=50, null=True),
        ),
    ]
