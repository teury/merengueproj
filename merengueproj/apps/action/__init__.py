from action.models import RegisteredAction


def get_action(name):
    return RegisteredAction.objects.get(name=name, category='action')
