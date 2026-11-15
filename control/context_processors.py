ROLE_LABELS = {
    'recepcao': 'Recepção',
    'central': 'Central de Atendimento',
    'profissional': 'Profissional',
}


def user_context(request):
    """Disponibiliza dados do usuário e dos grupos em todos os templates."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {
            'user_groups': [],
            'is_recepcao': False,
            'is_central': False,
            'is_profissional': False,
            'display_name': '',
            'user_role_label': 'Visitante',
            'user_initials': '',
        }

    group_names = list(user.groups.values_list('name', flat=True))
    display_name = user.get_full_name().strip() or user.username
    if user.is_staff or user.is_superuser:
        role_label = 'Administrador'
    else:
        role_label = next(
            (ROLE_LABELS[name] for name in group_names if name in ROLE_LABELS),
            'Usuário',
        )
    initials = ''.join(part[0] for part in display_name.split()[:2]).upper()
    if not initials:
        initials = display_name[:1].upper()

    return {
        'user_groups': group_names,
        'is_recepcao': 'recepcao' in group_names,
        'is_central': 'central' in group_names,
        'is_profissional': 'profissional' in group_names,
        'display_name': display_name,
        'user_role_label': role_label,
        'user_initials': initials,
    }
