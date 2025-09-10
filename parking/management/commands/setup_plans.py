from django.core.management.base import BaseCommand
from parking.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Set up default subscription plans for ParkPing'

    def handle(self, *args, **options):
        self.stdout.write('Setting up default subscription plans...')
        
        # Free Plan
        free_plan, created = SubscriptionPlan.objects.get_or_create(
            plan_type='free',
            defaults={
                'name': 'Free Plan',
                'description': 'Basic plan for getting started with ParkPing. Limited features but perfect for trying out the service.',
                'price': 0.00,
                'currency': 'INR',
                'billing_cycle': 'monthly',
                'max_vehicles': 1,
                'max_phone_numbers': 1,
                'number_masking': False,
                'custom_qr_design': False,
                'priority_support': False,
                'analytics_dashboard': False,
                'logo_placement': False,
                'custom_branding': False,
                'qr_color_primary': '#000000',
                'qr_color_secondary': '#FFFFFF',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created Free Plan'))
        else:
            self.stdout.write('✓ Free Plan already exists')
        
        # Basic Plan
        basic_plan, created = SubscriptionPlan.objects.get_or_create(
            plan_type='basic',
            defaults={
                'name': 'Basic Plan',
                'description': 'Perfect for individual users who want more features and flexibility.',
                'price': 299.00,
                'currency': 'INR',
                'billing_cycle': 'monthly',
                'max_vehicles': 3,
                'max_phone_numbers': 2,
                'number_masking': True,
                'custom_qr_design': False,
                'priority_support': False,
                'analytics_dashboard': False,
                'logo_placement': False,
                'custom_branding': False,
                'qr_color_primary': '#000000',
                'qr_color_secondary': '#FFFFFF',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created Basic Plan'))
        else:
            self.stdout.write('✓ Basic Plan already exists')
        
        # Professional Plan
        pro_plan, created = SubscriptionPlan.objects.get_or_create(
            plan_type='pro',
            defaults={
                'name': 'Professional Plan',
                'description': 'Advanced features for power users and small businesses. Includes custom QR design and analytics.',
                'price': 599.00,
                'currency': 'INR',
                'billing_cycle': 'monthly',
                'max_vehicles': 10,
                'max_phone_numbers': 5,
                'number_masking': True,
                'custom_qr_design': True,
                'priority_support': True,
                'analytics_dashboard': True,
                'logo_placement': True,
                'custom_branding': False,
                'qr_color_primary': '#000000',
                'qr_color_secondary': '#FFFFFF',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created Professional Plan'))
        else:
            self.stdout.write('✓ Professional Plan already exists')
        
        # Enterprise Plan
        enterprise_plan, created = SubscriptionPlan.objects.get_or_create(
            plan_type='enterprise',
            defaults={
                'name': 'Enterprise Plan',
                'description': 'Full-featured plan for large organizations and businesses. Includes all features and custom branding.',
                'price': 1499.00,
                'currency': 'INR',
                'billing_cycle': 'monthly',
                'max_vehicles': 50,
                'max_phone_numbers': 20,
                'number_masking': True,
                'custom_qr_design': True,
                'priority_support': True,
                'analytics_dashboard': True,
                'logo_placement': True,
                'custom_branding': True,
                'qr_color_primary': '#000000',
                'qr_color_secondary': '#FFFFFF',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created Enterprise Plan'))
        else:
            self.stdout.write('✓ Enterprise Plan already exists')
        
        self.stdout.write(self.style.SUCCESS('\nAll subscription plans have been set up successfully!'))
        self.stdout.write('\nPlan Summary:')
        self.stdout.write(f'  • Free: ${free_plan.price} - {free_plan.max_vehicles} vehicle(s)')
        self.stdout.write(f'  • Basic: ${basic_plan.price} - {basic_plan.max_vehicles} vehicles, Number Masking')
        self.stdout.write(f'  • Professional: ${pro_plan.price} - {pro_plan.max_vehicles} vehicles, Custom QR, Analytics')
        self.stdout.write(f'  • Enterprise: ${enterprise_plan.price} - {enterprise_plan.max_vehicles} vehicles, All Features')
