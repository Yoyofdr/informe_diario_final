#!/usr/bin/env python3
"""
Script para crear los planes de suscripción si no existen
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_sniper.settings')
django.setup()

from alerts.models import Plan

def create_plans():
    """Crear los planes si no existen"""
    
    # Plan Individual
    individual, created = Plan.objects.get_or_create(
        slug='individual',
        defaults={
            'name': 'Plan Individual',
            'price': 3990,
            'plan_type': 'individual',
            'max_users': 1,
            'features': {
                'daily_reports': True,
                'email_alerts': True,
                'export_pdf': True,
                'priority_support': False,
                'api_access': False
            },
            'is_active': True
        }
    )
    
    if created:
        print("✅ Plan Individual creado")
    else:
        print("ℹ️  Plan Individual ya existe")
    
    # Plan Organización
    organization, created = Plan.objects.get_or_create(
        slug='organizacion',
        defaults={
            'name': 'Plan Organización',
            'price': 29990,
            'plan_type': 'organizacion',
            'max_users': 10,
            'features': {
                'daily_reports': True,
                'email_alerts': True,
                'export_pdf': True,
                'priority_support': True,
                'api_access': True,
                'multiple_users': True,
                'admin_panel': True
            },
            'is_active': True
        }
    )
    
    if created:
        print("✅ Plan Organización creado")
    else:
        print("ℹ️  Plan Organización ya existe")
    
    print("\n📊 Planes en la base de datos:")
    for plan in Plan.objects.all():
        print(f"  - {plan.name}: ${plan.price} CLP (slug: {plan.slug})")

if __name__ == '__main__':
    create_plans()