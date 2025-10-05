"""
Comando para inicializar los planes de suscripción
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from alerts.models import Plan
import json


class Command(BaseCommand):
    help = 'Inicializa los planes de suscripción disponibles'
    
    def handle(self, *args, **options):
        # Plan Individual
        individual_plan, created = Plan.objects.update_or_create(
            slug='individual',
            defaults={
                'name': 'Plan Individual',
                'plan_type': 'individual',
                'price': 3990,
                'description': 'Perfecto para profesionales independientes que necesitan estar informados',
                'max_users': 1,
                'features': {
                    'informes_diarios': True,
                    'alertas_email': True,
                    'historial_30_dias': True,
                    'busqueda_avanzada': True,
                    'exportar_pdf': True,
                    'soporte_email': True,
                    'actualizaciones': True,
                }
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Plan Individual creado: ${individual_plan.price:,} CLP'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️ Plan Individual actualizado: ${individual_plan.price:,} CLP'))
        
        # Plan Organización
        organization_plan, created = Plan.objects.update_or_create(
            slug='organizacion',
            defaults={
                'name': 'Plan Organización',
                'plan_type': 'organizacion',
                'price': 29990,
                'description': 'Ideal para equipos y empresas que necesitan múltiples usuarios y características avanzadas',
                'max_users': 10,
                'features': {
                    'informes_diarios': True,
                    'alertas_email': True,
                    'historial_ilimitado': True,
                    'busqueda_avanzada': True,
                    'exportar_pdf': True,
                    'exportar_excel': True,
                    'api_access': True,
                    'integraciones': True,
                    'soporte_prioritario': True,
                    'capacitacion': True,
                    'personalizacion': True,
                    'multiples_usuarios': True,
                    'dashboard_analytics': True,
                    'alertas_personalizadas': True,
                    'actualizaciones': True,
                }
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Plan Organización creado: ${organization_plan.price:,} CLP'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️ Plan Organización actualizado: ${organization_plan.price:,} CLP'))
        
        self.stdout.write(self.style.SUCCESS('\n✨ Planes inicializados correctamente'))
        
        # Mostrar resumen
        self.stdout.write('\n' + '='*50)
        self.stdout.write('RESUMEN DE PLANES:')
        self.stdout.write('='*50)
        
        for plan in Plan.objects.filter(is_active=True):
            self.stdout.write(f'\n📋 {plan.name}')
            self.stdout.write(f'   Precio: ${plan.price:,} CLP/mes')
            self.stdout.write(f'   Usuarios: {plan.max_users}')
            self.stdout.write(f'   Características: {len(plan.features)} incluidas')