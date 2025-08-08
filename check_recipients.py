from alerts.models import Destinatario

print(f'Total destinatarios activos: {Destinatario.objects.filter(activo=True).count()}')
print(f'Total destinatarios: {Destinatario.objects.count()}')
print('\nLista de destinatarios:')
for dest in Destinatario.objects.all():
    print(f'- {dest.email} (activo: {dest.activo})')