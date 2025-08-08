from alerts.models import Destinatario

print(f'Total destinatarios: {Destinatario.objects.count()}')
print('\nLista de destinatarios:')
for dest in Destinatario.objects.all():
    print(f'- {dest.email} ({dest.nombre} - {dest.organizacion.nombre if dest.organizacion else "Sin org"})')