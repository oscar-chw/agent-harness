"""One explicit install preference; native clients retain final permission authority."""
MODES = ('preserve', 'explicit', 'autonomous')


def validate(value):
    if value not in MODES:
        raise ValueError('unknown permission profile; choose preserve, explicit or autonomous')
    return value


def choose(requested, saved, interactive=False):
    if requested is not None:
        return validate(requested)
    if saved is not None:
        return validate(saved)
    if not interactive:
        return 'preserve'
    answer = input('Permission control: 1 explicit review, 2 native workspace autonomy, '
                   '3 keep current settings [3]: ').strip()
    if answer not in ('', '1', '2', '3'):
        raise ValueError('invalid permission choice; nothing installed')
    return {'1': 'explicit', '2': 'autonomous', '3': 'preserve', '': 'preserve'}[answer]
